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
from dataclasses import dataclass, field
from typing import Any

import httpx

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

    async def aclose(self) -> None:
        """关闭底层连接（由应用生命周期调用）。"""
        await self._http.aclose()

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
        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._http.post("/chat/completions", json=payload)
                resp.raise_for_status()
                body = resp.json()
                usage = body.get("usage") or {}
                self.usage = Usage(
                    prompt_tokens=int(usage.get("prompt_tokens") or 0),
                    completion_tokens=int(usage.get("completion_tokens") or 0),
                )
                content = body["choices"][0]["message"]["content"]
                return self._parse_json(content)
            except (httpx.HTTPError, LLMError, KeyError, json.JSONDecodeError) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    logger.warning("LLM 调用失败(第 %d 次重试): %s", attempt + 1, exc)
                    continue
        raise LLMError(f"LLM 调用失败: {last_exc}")

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        """解析模型 JSON 输出，失败则尝试提取首个 JSON 对象块。"""
        text = content.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            raise LLMError("模型输出非合法 JSON")


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
        self._enabled = False
        self.reset()

    def reset(self) -> None:
        """按当前配置（重新）初始化客户端。"""
        self._enabled = settings.llm_enabled and bool(
            settings.llm_base_url and settings.llm_api_key and settings.llm_model
        )
        if not self._enabled:
            self._client = None
            logger.info("LLM 未启用，使用规则模式（降级）")
            return
        if self._client is None or self._client.model != settings.llm_model:
            old = self._client
            self._client = LLMClient(
                settings.llm_base_url,
                settings.llm_api_key,
                settings.llm_model,
                timeout_seconds=settings.llm_timeout_seconds,
                max_retries=settings.llm_max_retries,
                temperature=settings.llm_temperature,
            )
            if old is not None:
                import asyncio

                asyncio.get_event_loop().create_task(old.aclose())
        logger.info("LLM 已启用: model=%s", settings.llm_model)

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

    # ---- 领域接口：全部带降级 ----

    async def confirm_vuln(
        self,
        *,
        vuln_title: str,
        risk_level: str,
        file_path: str,
        evidence: str,
        context: str,
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
            return ConfirmResult(
                is_real=bool(data.get("is_real", True)),
                confidence=float(data.get("confidence", 0.0)),
                risk_level=str(data.get("risk_level", risk_level)),
                reason=str(data.get("reason", "")),
            )
        except LLMError as exc:
            logger.warning("confirm_vuln 降级: %s", exc)
            return None

    async def verify_vuln(
        self,
        *,
        vuln_title: str,
        file_path: str,
        evidence: str,
        context: str,
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
            return (
                str(data.get("reproduce_steps", "")),
                str(data.get("verify_code", "")),
            )
        except LLMError as exc:
            logger.warning("verify_vuln 降级: %s", exc)
            return None

    async def build_attack_path(
        self, vuln_items: list[dict[str, str]]
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
            return PathPlan(
                title=str(data.get("title", "综合攻击路径")),
                summary=str(data.get("summary", "")),
                final_impact=str(data.get("final_impact", "")),
                steps=steps,
            )
        except LLMError as exc:
            logger.warning("build_attack_path 降级: %s", exc)
            return None

    async def summarize_report(
        self,
        *,
        project_name: str,
        vuln_summary: str,
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
            return ReportEnhancement(
                summary=str(data.get("summary", "")),
                remediation=str(data.get("remediation", "")),
            )
        except LLMError as exc:
            logger.warning("summarize_report 降级: %s", exc)
            return None


llm_service = LLMService()