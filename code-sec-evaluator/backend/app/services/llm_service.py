"""LLM 语义增强服务：规则预筛之上的可选增强层（对齐《LLM集成实施文档》L02）。

职责：
- LLMClient：OpenAI 兼容协议（httpx 异步，base_url 指向 openai/qwen/deepseek/ollama），
  强制 JSON 结构化输出，累计 token 用量；
- LLMService：面向 worker 的领域接口（confirm/verify/attack_path/summarize）+ 全局降级。

降级原则（P2）：任何异常一律捕获并返回 None/默认值，logger.warning 提示；
LLM 不启用或未配置时，调用方保持现有规则逻辑（AC-7 演示闭环不破坏）。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.utils.logging import mask

logger = logging.getLogger("app.llm")

# 默认单次送审的上下文行数（降低成本与延迟）
_DEFAULT_CONTEXT_LINES = 30


class LLMError(Exception):
    """LLM 调用失败（超时/HTTP 错误/解析失败）。"""


@dataclass(frozen=True)
class Usage:
    """一次评估累计的 token 用量（真实计量，供 ops 阶段采集）。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True)
class LLMRuntimeConfig:
    """项目启动时冻结的 LLM 运行配置。"""

    enabled: bool
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int = 120
    max_retries: int = 2
    temperature: float = 0.1

    @property
    def ready(self) -> bool:
        return self.enabled and bool(self.base_url and self.api_key and self.model)

    @classmethod
    def from_settings(cls) -> LLMRuntimeConfig:
        return cls(
            enabled=settings.llm_enabled,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
            temperature=settings.llm_temperature,
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> LLMRuntimeConfig:
        return cls(
            enabled=bool(data.get("enabled")),
            base_url=str(data.get("base_url") or ""),
            api_key=str(data.get("api_key") or ""),
            model=str(data.get("model") or ""),
            timeout_seconds=int(
                data.get("timeout_seconds") or settings.llm_timeout_seconds
            ),
            max_retries=int(data.get("max_retries") or settings.llm_max_retries),
            temperature=float(data.get("temperature") or settings.llm_temperature),
        )


class LLMClient:
    """OpenAI 兼容协议客户端（httpx 异步）。"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        timeout_seconds: int = 120,
        max_retries: int = 2,
        temperature: float = 0.1,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self._max_retries = max_retries
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        self.usage = Usage()
        # 每次调用结束后产生的审计记录（成功/失败都会附加一条），由上层捕获落库
        self._calls: list[dict[str, Any]] = []

    async def aclose(self) -> None:
        """关闭底层连接（由应用生命周期调用）。"""
        await self._http.aclose()

    def _record_call(
        self,
        messages: list[dict[str, str]],
        resp_content: str | None,
        prompt_tokens: int,
        completion_tokens: int,
        *,
        ok: bool,
        note: str | None = None,
    ) -> None:
        """记录一次 LLM 调用（原始请求/响应/token/成败），供上层落库审计。"""
        self._calls.append(
            {
                "raw_request": json.dumps(messages, ensure_ascii=False),
                "raw_response": resp_content if ok else (note or ""),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "ok": ok,
            }
        )

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """请求 chat/completions 并解析 JSON 输出。

        Args:
            messages: OpenAI 风格消息数组（system/user/assistant）。
            temperature: 覆盖默认温度（判定类调用建议低值）。

        Returns:
            解析后的 JSON 对象。

        Raises:
            LLMError: 请求失败或返回不可解析的 JSON。
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
        }
        # 请求 JSON 输出（多数 OpenAI 兼容端点支持；不支持时走解析兜底）
        payload.setdefault("response_format", {"type": "json_object"})

        last_exc: Exception | None = None
        content: str | None = None
        prompt_tokens = completion_tokens = 0
        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._http.post("/chat/completions", json=payload)
                resp.raise_for_status()
                body = resp.json()
                logger.info("LLM 调用成功: %s", body)
                usage = body.get("usage") or {}
                prompt_tokens = int(usage.get("prompt_tokens") or 0)
                completion_tokens = int(usage.get("completion_tokens") or 0)
                self.usage = Usage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
                content = body["choices"][0]["message"]["content"]
                self._record_call(
                    messages, content, prompt_tokens, completion_tokens, ok=True
                )
                return self._parse_json(content)
            except (httpx.HTTPError, LLMError, KeyError, json.JSONDecodeError) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    logger.warning("LLM 调用失败(第 %d 次重试): %s", attempt + 1, exc)
                    continue
        self._record_call(messages, content, 0, 0, ok=False, note=str(last_exc))
        raise LLMError(f"LLM 调用失败: {last_exc}")

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        """解析模型 JSON 输出，失败则尝试提取首个 JSON 对象块。"""
        text = content.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            raise LLMError("模型输出非合法 JSON") from exc


@dataclass
class ConfirmResult:
    """code_analyze 命中确认结果（去误报）。"""

    is_real: bool
    confidence: float
    risk_level: str
    reason: str


@dataclass(frozen=True)
class PathStep:
    """攻击路径中的一个利用步骤。"""

    vuln_code: str
    step_text: str


@dataclass(frozen=True)
class PathPlan:
    """LLM 生成的攻击路径计划（复用 attack_path_service 落库）。"""

    title: str
    summary: str
    final_impact: str
    steps: list[PathStep]


@dataclass
class ReportEnhancement:
    """报告语义增强：摘要 + 修复建议。"""

    summary: str
    remediation: str


class LLMService:
    """面向 worker 的 LLM 领域接口；未启用/未配置时全部返回默认值（降级）。"""

    def __init__(self) -> None:
        self._client: LLMClient | None = None
        self._client_config: LLMRuntimeConfig | None = None
        self._enabled = False
        self._pending_logs: list[dict[str, Any]] = []
        self.reset()

    def reset(self) -> None:
        """按当前配置（重新）初始化客户端。"""
        self.reset_with_config(LLMRuntimeConfig.from_settings())

    def reset_with_config(self, config: LLMRuntimeConfig) -> None:
        """按项目启动时的配置快照初始化客户端。"""
        self._enabled = config.ready
        if not self._enabled:
            self._client = None
            self._client_config = None
            logger.info("LLM 未启用，使用规则模式（降级）")
            return
        if self._client is None or self._client_config != config:
            old = self._client
            self._client = LLMClient(
                config.base_url,
                config.api_key,
                config.model,
                timeout_seconds=config.timeout_seconds,
                max_retries=config.max_retries,
                temperature=config.temperature,
            )
            if old is not None:
                import asyncio

                asyncio.get_event_loop().create_task(old.aclose())
            self._client_config = config
        logger.info("LLM 已启用: model=%s", config.model)

    @property
    def enabled(self) -> bool:
        """LLM 是否启用且可调用。"""
        return self._enabled and self._client is not None

    @property
    def usage(self) -> Usage:
        """最近一个客户端的累计用量（ops 阶段采集）。"""
        return self._client.usage if self._client is not None else Usage()

    def reset_usage(self) -> None:
        """清零用量（每次项目评估前调用）。"""
        if self._client is not None:
            self._client.usage = Usage()

    async def aclose(self) -> None:
        """关闭客户端（应用退出时调用）。"""
        if self._client is not None:
            await self._client.aclose()

    # ---- LLM 调用审计（L07）----

    def _capture(
        self,
        task_type: str,
        *,
        project_id: int,
        stage_id: int | None,
        vuln_id: int | None,
    ) -> None:
        """从客户端取最近一次调用记录，补全上下文后缓冲（供 flush_logs 落库）。"""
        if self._client is None or not self._client._calls:
            return
        call = self._client._calls.pop()
        self._pending_logs.append(
            {
                "project_id": project_id,
                "stage_id": stage_id,
                "vuln_id": vuln_id,
                "model": self._client.model,
                "task_type": task_type,
                "raw_request": call["raw_request"],
                "raw_response": call["raw_response"],
                "prompt_tokens": call["prompt_tokens"],
                "completion_tokens": call["completion_tokens"],
                "fallback": not call["ok"],
            }
        )

    def pending_log_count(self) -> int:
        """缓冲中的待落库审计记录数（可用于观测）。"""
        return len(self._pending_logs)

    async def flush_logs(self, db: AsyncSession) -> int:
        """将缓冲的 LLM 调用审计记录批量写入 ``llm_analysis_logs``。"""
        if not self._pending_logs:
            return 0
        from app.models.llm_analysis_log import (
            LLMAnalysisLog,  # noqa: F401  延迟导入避循环
        )

        db.add_all([LLMAnalysisLog(**entry) for entry in self._pending_logs])
        count = len(self._pending_logs)
        self._pending_logs.clear()
        return count

    async def list_logs(
        self,
        db: AsyncSession,
        project_id: int,
        *,
        task_type: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[int, list[dict[str, Any]]]:
        """分页查询项目 LLM 调用日志（可回溯审计）。

        Returns:
            (total, items) 元组；items 不含原始请求/响应全文（体积过大），
            需要明细时后续可扩展独立详情端点。
        """
        from app.models.llm_analysis_log import LLMAnalysisLog

        stmt = select(LLMAnalysisLog).where(LLMAnalysisLog.project_id == project_id)
        count_stmt = select(func.count()).where(LLMAnalysisLog.project_id == project_id)
        if task_type:
            stmt = stmt.where(LLMAnalysisLog.task_type == task_type)
            count_stmt = count_stmt.where(LLMAnalysisLog.task_type == task_type)
        total = int((await db.scalar(count_stmt)) or 0)
        rows = (
            (
                await db.execute(
                    stmt.order_by(LLMAnalysisLog.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        items = [
            {
                "id": row.id,
                "project_id": row.project_id,
                "stage_id": row.stage_id,
                "vuln_id": row.vuln_id,
                "model": row.model,
                "task_type": row.task_type,
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "fallback": row.fallback,
                "created_at": row.created_at,
            }
            for row in rows
        ]
        return total, items

    # ---- 领域接口：全部带降级 ----

    async def confirm_vuln(
        self,
        *,
        vuln_title: str,
        risk_level: str,
        file_path: str,
        evidence: str,
        context: str,
        project_id: int,
        stage_id: int | None = None,
        vuln_id: int | None = None,
    ) -> ConfirmResult | None:
        """确认规则命中是否为真实漏洞（去误报）。

        Returns:
            ConfirmResult；LLM 降级时返回 None（调用方应保留原候选）。
        """
        if not self.enabled:
            return None
        system = (
            "你是资深代码安全审计专家。给定一个规则命中的候选漏洞，请判断它是否是"
            "真实可利用的安全漏洞。只输出 JSON，不要包含其他文字，格式："
            '{"is_real": true/false, "confidence": 0~1, "risk_level": "critical/high/medium/low",'
            ' "reason": "简短判断理由"}。'
        )
        user = (
            f"规则标题：{vuln_title}\n"
            f"建议风险等级：{risk_level}\n"
            f"命中文件：{file_path}\n"
            f"命中证据：\n{mask(evidence)}\n\n"
            f"代码上下文：\n{mask(context)}\n"
        )
        try:
            data = await self._client.chat_json(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
            )
            self._capture(
                "confirm",
                project_id=project_id,
                stage_id=stage_id,
                vuln_id=vuln_id,
            )
            return ConfirmResult(
                is_real=bool(data.get("is_real", True)),
                confidence=float(data.get("confidence", 0.0)),
                risk_level=str(data.get("risk_level", risk_level)),
                reason=str(data.get("reason", "")),
            )
        except LLMError as exc:
            self._capture(
                "confirm",
                project_id=project_id,
                stage_id=stage_id,
                vuln_id=vuln_id,
            )
            logger.warning("confirm_vuln 降级: %s", exc)
            return None

    async def verify_vuln(
        self,
        *,
        vuln_title: str,
        file_path: str,
        evidence: str,
        context: str,
        project_id: int,
        stage_id: int | None = None,
        vuln_id: int | None = None,
    ) -> tuple[str, str] | None:
        """生成真实复现步骤与 PoC 骨架（回填 reproduce/verify 字段）。

        Returns:
            (reproduce_steps, verify_code) 元组；降级时返回 None。
        """
        if not self.enabled:
            return None
        system = (
            "你是代码安全 PoC 生成专家。给定一个已确认的漏洞，输出 JSON，格式："
            '{"reproduce_steps": "从攻击者视角的分步复现步骤（含触发请求/输入样例）",'
            ' "verify_code": "一个最小可运行的 PoC 代码骨架（带注释说明）"}。'
            "只输出 JSON。"
        )
        user = (
            f"漏洞标题：{vuln_title}\n"
            f"文件位置：{file_path}\n"
            f"证据：\n{mask(evidence)}\n\n"
            f"代码上下文：\n{mask(context)}\n"
        )
        try:
            data = await self._client.chat_json(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            self._capture(
                "verify",
                project_id=project_id,
                stage_id=stage_id,
                vuln_id=vuln_id,
            )
            return (
                str(data.get("reproduce_steps", "")),
                str(data.get("verify_code", "")),
            )
        except LLMError as exc:
            self._capture(
                "verify",
                project_id=project_id,
                stage_id=stage_id,
                vuln_id=vuln_id,
            )
            logger.warning("verify_vuln 降级: %s", exc)
            return None

    async def build_attack_path(
        self,
        vuln_items: list[dict[str, str]],
        *,
        project_id: int,
        stage_id: int | None = None,
    ) -> PathPlan | None:
        """按数据流/利用前置语义串联漏洞生成攻击路径计划。

        Args:
            vuln_items: [{"vuln_code", "vuln_title", "risk_level", "file_path"}]

        Returns:
            PathPlan；降级时返回 None（调用方维持按 risk 排序的默认路径）。
        """
        if not self.enabled:
            return None
        catalog = "\n".join(
            f"- {item['vuln_code']} | {item['vuln_title']} | {item['risk_level']} | {item['file_path']}"
            for item in vuln_items
        )
        system = (
            "你是攻击链编排专家。给定已确认漏洞清单，按真实可利用的先后依赖关系编排"
            "攻击路径。只输出 JSON，格式："
            '{"title": "...", "summary": "...", "final_impact": "...",'
            ' "steps": [{"vuln_code": "...", "step_text": "..."}]}。step 按利用顺序排列。'
        )
        user = f"漏洞清单：\n{catalog}\n"
        try:
            data = await self._client.chat_json(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            raw_steps = data.get("steps") or []
            steps = [
                PathStep(
                    vuln_code=str(step.get("vuln_code", "")),
                    step_text=str(step.get("step_text", "")),
                )
                for step in raw_steps
            ]
            self._capture(
                "attack_path",
                project_id=project_id,
                stage_id=stage_id,
                vuln_id=None,
            )
            return PathPlan(
                title=str(data.get("title", "综合攻击路径")),
                summary=str(data.get("summary", "")),
                final_impact=str(data.get("final_impact", "")),
                steps=steps,
            )
        except LLMError as exc:
            self._capture(
                "attack_path",
                project_id=project_id,
                stage_id=stage_id,
                vuln_id=None,
            )
            logger.warning("build_attack_path 降级: %s", exc)
            return None

    async def summarize_report(
        self,
        *,
        project_name: str,
        vuln_summary: str,
        project_id: int,
        stage_id: int | None = None,
    ) -> ReportEnhancement | None:
        """生成报告摘要与定制修复建议（供 _build_markdown 渲染）。"""
        if not self.enabled:
            return None
        system = (
            "你是安全评估报告撰写专家。给定漏洞汇总，输出 JSON，格式："
            '{"summary": "一段评估总体结论与风险概览", "remediation": "针对本次发现的定制修复建议"}。'
            "只输出 JSON。"
        )
        user = f"项目：{project_name}\n漏洞汇总：\n{vuln_summary}\n"
        try:
            data = await self._client.chat_json(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.4,
            )
            self._capture(
                "summary",
                project_id=project_id,
                stage_id=stage_id,
                vuln_id=None,
            )
            return ReportEnhancement(
                summary=str(data.get("summary", "")),
                remediation=str(data.get("remediation", "")),
            )
        except LLMError as exc:
            self._capture(
                "summary",
                project_id=project_id,
                stage_id=stage_id,
                vuln_id=None,
            )
            logger.warning("summarize_report 降级: %s", exc)
            return None


llm_service = LLMService()
