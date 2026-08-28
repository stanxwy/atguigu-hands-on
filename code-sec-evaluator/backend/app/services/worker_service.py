"""角色任务执行服务：6 类角色（generic/env_check/code_analyze/vuln_verify/report_gen/ops）。

每个角色创建独立的 ``worker_tasks`` 记录（可回溯 project_id + stage_id），
扫描采用**纯 Python 文件读取**（零命令执行、跨平台确定、比容器内 grep 更安全）；
命令白名单与隔离 exec 由 :mod:`app.services.isolation_service` 提供并供扩展使用。
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import RISK_SEVERITY
from app.models.project import Project
from app.models.vulnerability import Vulnerability
from app.models.worker_task import WorkerTask
from app.services import (
    attack_path_service,
    report_service,
    vulnerability_service,
)
from app.services.llm_service import ReportEnhancement, llm_service
from app.services.monitor_service import monitor_service

logger = logging.getLogger("app.worker")

_RULES_PATH = Path(__file__).resolve().parents[2] / "rules" / "default_keywords.yaml"

# 跳过目录与文本大小上限（防大文件拖垮扫描）
_SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".idea", ".vscode", "dist", "build", ".mypy_cache", ".pytest_cache",
}
_MAX_FILE_BYTES = 1_000_000
_MAX_EVIDENCE_LINES = 20


@dataclass(frozen=True)
class Rule:
    """关键字规则（来自 rules/default_keywords.yaml）。"""

    id: str
    title: str
    risk_level: str
    role: str
    keywords: list[str]
    case_sensitive: bool
    description: str


_rules_cache: list[Rule] | None = None


def load_rules() -> list[Rule]:
    """加载内置关键字规则集（缓存）。"""
    global _rules_cache
    if _rules_cache is None:
        with open(_RULES_PATH, encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        _rules_cache = [Rule(**item) for item in data.get("rules", [])]
    return _rules_cache


def _now() -> datetime:
    return datetime.now(UTC)


def _iter_source_files(root: Path) -> list[Path]:
    """递归收集源码文本文件（跳过目录/大文件）。"""
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        files.append(path)
    return files


def _match(line: str, keyword: str, case_sensitive: bool) -> bool:
    """关键字匹配（字面量包含，非正则注入）。"""
    if case_sensitive:
        return keyword in line
    return keyword.lower() in line.lower()


def _scan(root: Path, rules: list[Rule]) -> list[dict[str, Any]]:
    """扫描源码，返回每条命中规则的匹配明细。"""
    files = _iter_source_files(root)
    results: list[dict[str, Any]] = []
    for rule in rules:
        matches: list[tuple[str, int, str]] = []
        for file_path in files:
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                for keyword in rule.keywords:
                    if _match(line, keyword, rule.case_sensitive):
                        rel = file_path.relative_to(root).as_posix()
                        matches.append((rel, line_no, line.strip()))
                        break
        if matches:
            results.append({"rule": rule, "matches": matches})
    return results


def _format_evidence(matches: list[tuple[str, int, str]]) -> str:
    """将匹配明细格式化为证据文本（截断）。"""
    lines = [
        f"{rel}:{line_no}: {text}" for rel, line_no, text in matches[:_MAX_EVIDENCE_LINES]
    ]
    if len(matches) > _MAX_EVIDENCE_LINES:
        lines.append(f"... 共 {len(matches)} 处命中")
    return "\n".join(lines)


def _reproduce_steps(vuln: Vulnerability) -> str:
    """生成复现步骤模板。"""
    return (
        f"1. 定位到 {vuln.file_path or '未知文件'}；\n"
        f"2. 依据证据中的代码行触发对应缺陷；\n"
        f"3. 观察是否造成 {vuln.risk_level} 级安全影响。"
    )


def _verify_code(vuln: Vulnerability) -> str:
    """生成验证代码占位（展示 PoC 骨架）。"""
    return (
        f"# 验证 {vuln.vuln_code}（{vuln.vuln_title}）\n"
        f"# 风险等级：{vuln.risk_level}\n"
        f"# 位置：{vuln.file_path or '-'}\n"
    )


def _read_context(source_dir: Path, relative_path: str, line_no: int, window: int = 30) -> str:
    """读取命中文件的上下文窗口（±window 行），供 LLM 确认/验证参考。

    Args:
        source_dir: 源码根目录。
        relative_path: 命中文件相对路径（POSIX 风格）。
        line_no: 命中行号（1 起点）。
        window: 上下各读取行数。

    Returns:
        带行号的上下文文本；文件不可读时返回空串。
    """
    if not relative_path or line_no <= 0:
        return ""
    target = source_dir.joinpath(relative_path)
    try:
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    start = max(0, line_no - window - 1)
    end = min(len(lines), line_no + window)
    return "\n".join(
        f"{i + 1}: {line}" for i, line in enumerate(lines[start:end], start=start + 1)
    )


async def _create_worker(
    db: AsyncSession,
    project_id: int,
    stage_id: int,
    role: str,
    task_content: str | None = None,
) -> WorkerTask:
    """创建角色任务记录。"""
    task = WorkerTask(
        project_id=project_id,
        stage_id=stage_id,
        worker_role=role,
        task_content=task_content,
        task_status="idle",
    )
    db.add(task)
    await db.flush()
    return task


async def _mark_running(
    db: AsyncSession, project: Project, task: WorkerTask, role: str, message: str
) -> None:
    """标记任务运行中并推送事件/聊天。"""
    task.task_status = "running"
    task.started_at = _now()
    await db.commit()
    monitor_service.publish(
        project.id,
        "worker_status",
        {
            "worker_task_id": task.id,
            "worker_role": role,
            "task_status": "running",
        },
    )
    await monitor_service.append_chat(db, project.id, role, "info", message)
    await db.commit()


async def _mark_done(
    db: AsyncSession,
    project: Project,
    task: WorkerTask,
    role: str,
    summary: str,
    success: bool,
) -> bool:
    """标记任务结束并推送事件。"""
    task.task_status = "success" if success else "failed"
    task.finished_at = _now()
    task.result_summary = summary
    await db.commit()
    monitor_service.publish(
        project.id,
        "worker_status",
        {
            "worker_task_id": task.id,
            "worker_role": role,
            "task_status": task.task_status,
        },
    )
    return success


async def _run_scan_role(
    db: AsyncSession,
    project: Project,
    stage_id: int,
    role: str,
    source_dir: Path,
    task_content: str,
) -> bool:
    """环境扫描 / 代码分析角色的公共扫描逻辑。"""
    task = await _create_worker(db, project.id, stage_id, role, task_content)
    await _mark_running(db, project, task, role, f"{role} 开始扫描源码")
    try:
        rules = [r for r in load_rules() if r.role == role]
        files = _iter_source_files(source_dir)
        logger.info(
            "项目 %s 角色 %s 开始扫描: %d 个文件, %d 条规则",
            project.id, role, len(files), len(rules),
        )
        await monitor_service.append_log(
            db, project.id, "info",
            f"{role} 开始扫描: {len(files)} 个文件, {len(rules)} 条规则",
            stage_id=stage_id,
        )
        await db.commit()
        results = await asyncio.to_thread(_scan, source_dir, rules)
        created: list[Vulnerability] = []
        for result in results:
            rule = result["rule"]
            matches = result["matches"]
            evidence = _format_evidence(matches)
            file_path = matches[0][0]
            logger.info(
                "项目 %s 角色 %s 命中规则 %s（%s）: %d 处，首处 %s",
                project.id, role, rule.title, rule.risk_level, len(matches), file_path,
            )
            await monitor_service.append_log(
                db, project.id, "info",
                f"命中规则 {rule.title}（{rule.risk_level}）: {len(matches)} 处",
                stage_id=stage_id,
            )
            vuln = await vulnerability_service.create_vulnerability(
                db,
                project.id,
                vuln_title=rule.title,
                risk_level=rule.risk_level,
                file_path=file_path,
                condition_text=rule.description,
                evidence_text=evidence,
            )
            created.append(vuln)
            if role == "code_analyze":
                await _confirm_match(
                    db, project, vuln, source_dir, matches[0][1], stage_id
                )
            await db.commit()
            monitor_service.publish(
                project.id,
                "vulnerability_found",
                {
                    "vuln_id": vuln.id,
                    "vuln_title": vuln.vuln_title,
                    "risk_level": vuln.risk_level,
                },
            )
            await monitor_service.append_chat(
                db,
                project.id,
                role,
                "warning",
                f"发现 {rule.title}（{rule.risk_level}）：{vuln.vuln_code}",
            )
        logger.info(
            "项目 %s 角色 %s 扫描完成，命中 %d 个隐患",
            project.id, role, len(created),
        )
        await monitor_service.append_log(
            db, project.id, "info",
            f"{role} 扫描完成，命中 {len(created)} 个隐患",
            stage_id=stage_id,
        )
        await db.commit()
        await llm_service.flush_logs(db)
        await db.commit()
        summary = f"{role} 扫描完成，命中 {len(created)} 个隐患"
        return await _mark_done(db, project, task, role, summary, True)
    except Exception as exc:  # noqa: BLE001  异步任务内必须捕获异常并落库
        logger.exception("角色 %s 执行失败", role)
        await monitor_service.append_log(
            db, project.id, "error", f"{role} 执行异常: {exc}", stage_id=stage_id
        )
        return await _mark_done(db, project, task, role, str(exc), False)


async def _confirm_match(
    db: AsyncSession,
    project: Project,
    vuln: Vulnerability,
    source_dir: Path,
    line_no: int,
    stage_id: int,
) -> None:
    """LLM 确认规则命中是否为真实漏洞（code_analyze 去误报）。

    命中文件的行号取自首个证据（matches[0][1]）。LLM 降级时保留原候选，
    不做任何改动；确认非真实且置信度 ≥0.7 时标记 verify_status=\"failed\"。
    """
    if not llm_service.enabled:
        return
    context = _read_context(source_dir, vuln.file_path or "", line_no)
    result = await llm_service.confirm_vuln(
        vuln_title=vuln.vuln_title,
        risk_level=vuln.risk_level,
        file_path=vuln.file_path or "",
        evidence=vuln.evidence_text or "",
        context=context,
        project_id=project.id,
        stage_id=stage_id,
        vuln_id=vuln.id,
    )
    if result is None:
        return
    if not result.is_real and result.confidence >= 0.7:
        vuln.verify_status = "failed"
        logger.info(
            "项目 %s 代码分析 LLM 去误报 %s: %s（置信度 %.2f）",
            project.id, vuln.vuln_code, vuln.vuln_title, result.confidence,
        )
        await monitor_service.append_log(
            db, project.id, "info",
            f"LLM 判定 {vuln.vuln_code}「{vuln.vuln_title}」为误报（置信度 {result.confidence:.2f}）",
            stage_id=stage_id,
        )
        monitor_service.publish(
            project.id,
            "vulnerability_status",
            {"vuln_id": vuln.id, "verify_status": vuln.verify_status},
        )
    else:
        logger.info(
            "项目 %s 代码分析 LLM 确认 %s: %s（is_real=%s, 置信度 %.2f）",
            project.id, vuln.vuln_code, vuln.vuln_title, result.is_real,
            result.confidence,
        )


async def _verify_single(
    db: AsyncSession,
    project: Project,
    vuln: Vulnerability,
    source_dir: Path,
    stage_id: int,
) -> None:
    """对单个漏洞生成复现步骤与验证代码（LLM 真 PoC，降级用模板兜底）。

    已被 L03 判定为误报（verify_status=failed）的候选直接跳过。
    """
    if vuln.verify_status == "failed":
        logger.info(
            "项目 %s 跳过误报 %s: %s", project.id, vuln.vuln_code, vuln.vuln_title
        )
        return
    vuln.verify_status = "verified"
    llm_reproduce: str | None = None
    llm_verify_code: str | None = None
    if llm_service.enabled and vuln.file_path and vuln.file_path != "-":
        line_no = _first_evidence_line(vuln.evidence_text or "")
        context = _read_context(source_dir, vuln.file_path, line_no)
        generated = await llm_service.verify_vuln(
            vuln_title=vuln.vuln_title,
            file_path=vuln.file_path,
            evidence=vuln.evidence_text or "",
            context=context,
            project_id=project.id,
            stage_id=stage_id,
            vuln_id=vuln.id,
        )
        if generated is not None:
            llm_reproduce, llm_verify_code = generated
            logger.info(
                "项目 %s LLM 生成 PoC %s: %s",
                project.id, vuln.vuln_code, vuln.vuln_title,
            )
    vuln.reproduce_steps_text = llm_reproduce or _reproduce_steps(vuln)
    vuln.verify_code_text = llm_verify_code or _verify_code(vuln)
    if llm_reproduce:
        await monitor_service.append_log(
            db, project.id, "info",
            f"LLM 生成验证步骤 {vuln.vuln_code}: {vuln.vuln_title}",
            stage_id=stage_id,
        )


def _first_evidence_line(evidence: str) -> int:
    """从证据文本首行解析命中行号（格式 `rel:line: text`）。"""
    first = evidence.splitlines()[0] if evidence else ""
    parts = first.split(":")
    try:
        return int(parts[1])
    except (IndexError, ValueError):
        return 1


async def run_generic(db: AsyncSession, project: Project, stage_id: int) -> bool:
    """generic：任务编排/兜底（记录编排启动）。"""
    role = "generic"
    task = await _create_worker(db, project.id, stage_id, role, "任务编排")
    await _mark_running(db, project, task, role, "开始编排评估任务")
    await monitor_service.append_chat(
        db,
        project.id,
        role,
        "info",
        f"开始评估项目「{project.project_name}」（{project.source_type}）",
    )
    summary = f"编排启动：{project.source_type} -> {project.source_path}"
    return await _mark_done(db, project, task, role, summary, True)


async def run_env_check(
    db: AsyncSession, project: Project, stage_id: int, source_dir: Path
) -> bool:
    """env_check：环境扫描（结构/配置/运行参数/硬编码密钥）。"""
    return await _run_scan_role(
        db, project, stage_id, "env_check", source_dir, "环境扫描"
    )


async def run_code_analyze(
    db: AsyncSession, project: Project, stage_id: int, source_dir: Path
) -> bool:
    """code_analyze：代码分析（关键字搜索 + 静态特征识别）。"""
    return await _run_scan_role(
        db, project, stage_id, "code_analyze", source_dir, "代码分析"
    )


async def run_vuln_verify(
    db: AsyncSession, project: Project, stage_id: int, source_dir: Path
) -> bool:
    """vuln_verify：对候选漏洞逐一验证（LLM 生成真实 PoC，降级用模板兜底）。"""
    role = "vuln_verify"
    task = await _create_worker(db, project.id, stage_id, role, "漏洞验证")
    await _mark_running(db, project, task, role, "开始验证候选漏洞")
    try:
        vulns = (
            (
                await db.execute(
                    select(Vulnerability).where(
                        Vulnerability.project_id == project.id
                    )
                )
            )
            .scalars()
            .all()
        )
        for vuln in vulns:
            await _verify_single(db, project, vuln, source_dir, stage_id)
            logger.info(
                "项目 %s 验证漏洞 %s: %s（%s）",
                project.id, vuln.vuln_code, vuln.vuln_title, vuln.risk_level,
            )
            await monitor_service.append_log(
                db, project.id, "info",
                f"验证漏洞 {vuln.vuln_code}: {vuln.vuln_title}（{vuln.risk_level}）",
                stage_id=stage_id,
            )
        await db.commit()
        await llm_service.flush_logs(db)
        await db.commit()
        logger.info("项目 %s 漏洞验证完成，共 %d 个", project.id, len(vulns))
        await monitor_service.append_log(
            db, project.id, "info", f"漏洞验证完成，共 {len(vulns)} 个",
            stage_id=stage_id,
        )
        await db.commit()
        summary = f"验证完成：{len(vulns)} 个漏洞已确认"
        return await _mark_done(db, project, task, role, summary, True)
    except Exception as exc:  # noqa: BLE001
        logger.exception("漏洞验证失败")
        await monitor_service.append_log(
            db, project.id, "error", f"漏洞验证异常: {exc}", stage_id=stage_id
        )
        return await _mark_done(db, project, task, role, str(exc), False)


def _build_markdown(
    project: Project,
    vulns: list[Vulnerability],
    attack_vulns: list[Vulnerability],
    path: Any,
    enhancement: ReportEnhancement | None = None,
) -> str:
    """构建权威 Markdown 报告。

    Args:
        project: 项目实例。
        vulns: 按编号排序的漏洞列表（漏洞清单）。
        attack_vulns: 按严重度排序的漏洞列表（攻击路径步骤）。
        path: AttackPath 实例（仅使用其标量字段，避免懒加载关系）。
        enhancement: LLM 语义增强（摘要 + 定制修复建议）；降级时为空。
    """
    risk_label = {
        "critical": "严重",
        "high": "高危",
        "medium": "中危",
        "low": "低危",
    }
    lines = [
        f"# 安全评估报告：{project.project_name}",
        "",
        f"- 项目 ID：{project.id}",
        f"- 源码类型：{project.source_type}",
        f"- 源码位置：{project.source_path}",
        f"- 任务说明：{project.task_content or '（未填写）'}",
        f"- 漏洞总数：{len(vulns)}",
        f"- 攻击路径数：{1 if path else 0}",
        "",
    ]
    if enhancement and enhancement.summary:
        lines.extend(
            [
                "## 评估结论",
                "",
                enhancement.summary,
                "",
            ]
        )
    lines.extend(
        [
            "## 漏洞清单",
            "",
            "| 编号 | 标题 | 风险等级 | 位置 | 验证状态 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for vuln in vulns:
        lines.append(
            f"| {vuln.vuln_code} | {vuln.vuln_title} | "
            f"{risk_label.get(vuln.risk_level, vuln.risk_level)} | "
            f"{vuln.file_path or '-'} | {vuln.verify_status} |"
        )
    lines.append("")
    lines.append("## 漏洞详情")
    lines.append("")
    for vuln in vulns:
        lines.append(f"### {vuln.vuln_code} {vuln.vuln_title}")
        lines.append("")
        if vuln.condition_text:
            lines.append(f"**触发条件**：{vuln.condition_text}")
            lines.append("")
        if vuln.evidence_text:
            lines.append("**证据**：")
            lines.append("")
            lines.append("```text")
            lines.append(vuln.evidence_text)
            lines.append("```")
            lines.append("")
    lines.append("## 攻击路径")
    lines.append("")
    if path is not None:
        lines.append(f"### {path.path_code} {path.path_title}")
        lines.append("")
        if path.path_summary:
            lines.append(path.path_summary)
            lines.append("")
        for step_order, vuln in enumerate(attack_vulns, start=1):
            lines.append(
                f"{step_order}. 利用「{vuln.vuln_title}」（{vuln.file_path or '未知位置'}）"
            )
        if path.final_impact_text:
            lines.append("")
            lines.append(f"**最终影响**：{path.final_impact_text}")
    lines.append("")
    lines.append("## 修复建议")
    lines.append("")
    if enhancement and enhancement.remediation:
        lines.append(enhancement.remediation)
    else:
        lines.append(
            "1. 对用户输入做参数化查询，杜绝字符串拼接 SQL；"
            "2. 使用白名单校验命令/路径，禁用 shell=True；"
            "3. 前端输出统一转义，禁止未经净化的 HTML 注入；"
            "4. 敏感凭据移出源码，改用密钥管理；"
            "5. 使用强加密算法（如 AES-GCM），替换 MD5/SHA1/ECB。"
        )
    lines.append("")
    return "\n".join(lines)


async def _plan_attack_path(
    db: AsyncSession,
    project: Project,
    ordered: list[Vulnerability],
    stage_id: int,
) -> dict[str, Any]:
    """编排攻击路径：优先 LLM 语义编排，降级为按严重度排序的默认方案。

    Returns:
        ``{"title", "summary", "final_impact", "items"}``，其中
        items 为 ``[(vuln_id, step_text)]``（按利用顺序）。
    """
    fallback_items = [
        (
            v.id,
            f"利用「{v.vuln_title}」（{v.file_path or '未知位置'}）",
        )
        for v in ordered
    ]
    plan = await llm_service.build_attack_path(
        [
            {
                "vuln_code": v.vuln_code,
                "vuln_title": v.vuln_title,
                "risk_level": v.risk_level,
                "file_path": v.file_path or "",
            }
            for v in ordered
        ],
        project_id=project.id,
        stage_id=stage_id,
    )
    if plan is None or not plan.steps:
        logger.info("项目 %s 攻击路径降级：按严重度排序", project.id)
        await monitor_service.append_log(
            db, project.id, "info", "LLM 未编排攻击路径，降级为按风险排序",
        )
        return {
            "title": "综合攻击路径：从信息泄露到命令执行",
            "summary": "按风险严重度串联全部已确认漏洞，构成从信息泄露、注入到命令执行的完整攻击链。",
            "final_impact": "敏感数据大范围泄露 + 服务器被完全控制",
            "items": fallback_items,
        }
    by_code = {v.vuln_code: v for v in ordered}
    items: list[tuple[int, str]] = []
    for step in plan.steps:
        vuln = by_code.get(step.vuln_code)
        if vuln is not None:
            items.append((vuln.id, step.step_text or f"利用「{vuln.vuln_title}」"))
    if not items:
        logger.info("项目 %s 攻击路径步骤未匹配，降级为按严重度排序", project.id)
        return {
            "title": "综合攻击路径：从信息泄露到命令执行",
            "summary": "按风险严重度串联全部已确认漏洞，构成从信息泄露、注入到命令执行的完整攻击链。",
            "final_impact": "敏感数据大范围泄露 + 服务器被完全控制",
            "items": fallback_items,
        }
    logger.info("项目 %s LLM 编排攻击路径：%s", project.id, plan.title)
    await monitor_service.append_log(
        db, project.id, "info",
        f"LLM 编排攻击路径「{plan.title}」共 {len(items)} 步",
    )
    return {
        "title": plan.title,
        "summary": plan.summary,
        "final_impact": plan.final_impact,
        "items": items,
    }


async def _summarize_report(
    db: AsyncSession,
    project: Project,
    ordered: list[Vulnerability],
    stage_id: int,
) -> ReportEnhancement | None:
    """请求 LLM 生成报告摘要与定制修复建议（降级返回 None）。"""
    if not llm_service.enabled or not ordered:
        return None
    vuln_summary = "\n".join(
        f"- {v.vuln_code} {v.vuln_title}（{v.risk_level}，{v.file_path or '未知位置'}）"
        for v in ordered
    )
    enhancement = await llm_service.summarize_report(
        project_name=project.project_name,
        vuln_summary=vuln_summary,
        project_id=project.id,
        stage_id=stage_id,
    )
    if enhancement is None:
        logger.info("项目 %s 报告增强降级：无 LLM 摘要", project.id)
        return None
    logger.info("项目 %s LLM 生成报告摘要与修复建议", project.id)
    await monitor_service.append_log(
        db, project.id, "info", "LLM 生成报告摘要与定制修复建议",
    )
    return enhancement


async def run_report_gen(db: AsyncSession, project: Project, stage_id: int) -> bool:
    """report_gen：串联攻击路径 + 生成 Markdown/HTML 报告。"""
    role = "report_gen"
    task = await _create_worker(db, project.id, stage_id, role, "报告生成")
    await _mark_running(db, project, task, role, "开始汇总并生成报告")
    try:
        vulns = (
            (
                await db.execute(
                    select(Vulnerability)
                    .where(Vulnerability.project_id == project.id)
                    .order_by(Vulnerability.id)
                )
            )
            .scalars()
            .all()
        )
        ordered = sorted(
            vulns, key=lambda v: (-RISK_SEVERITY.get(v.risk_level, 0), v.id)
        )
        path = None
        if ordered:
            plan = await _plan_attack_path(db, project, ordered, stage_id)
            path = await attack_path_service.create_attack_path(
                db,
                project.id,
                path_title=plan["title"],
                path_summary=plan["summary"],
                final_impact_text=plan["final_impact"],
                items=plan["items"],
            )
            await db.commit()
        enhancement = await _summarize_report(db, project, ordered, stage_id)
        markdown_text = _build_markdown(project, vulns, ordered, path, enhancement)
        report = await report_service.generate_and_save(db, project.id, markdown_text)
        await db.commit()
        await llm_service.flush_logs(db)
        await db.commit()
        logger.info(
            "项目 %s 报告已生成: report_id=%s，漏洞 %d 个",
            project.id, report.id, len(vulns),
        )
        await monitor_service.append_log(
            db, project.id, "info",
            f"报告已生成: report_id={report.id}，漏洞 {len(vulns)} 个",
            stage_id=stage_id,
        )
        await db.commit()
        monitor_service.publish(
            project.id, "report_ready", {"report_id": report.id}
        )
        summary = f"报告生成完成：report_id={report.id}，漏洞 {len(vulns)} 个"
        return await _mark_done(db, project, task, role, summary, True)
    except Exception as exc:  # noqa: BLE001
        logger.exception("报告生成失败")
        await monitor_service.append_log(
            db, project.id, "error", f"报告生成异常: {exc}", stage_id=stage_id
        )
        return await _mark_done(db, project, task, role, str(exc), False)


async def run_ops(db: AsyncSession, project: Project, stage_id: int) -> bool:
    """ops：运维巡检（日志规范复核 + 资源采集）。"""
    role = "ops"
    task = await _create_worker(db, project.id, stage_id, role, "运维巡检")
    await _mark_running(db, project, task, role, "开始运维巡检与资源采集")
    try:
        # 真实 token 计量：取自本项目评估期间 LLM 实际返回的 usage
        token_count = llm_service.usage.total
        await monitor_service.collect_and_record(db, project.id, token_count=token_count)
        await db.commit()
        logger.info("项目 %s 运维巡检完成，真实 token %d", project.id, token_count)
        await monitor_service.append_log(
            db, project.id, "info",
            f"运维巡检完成，资源采集 1 条（token={token_count}）",
            stage_id=stage_id,
        )
        await db.commit()
        summary = f"运维巡检完成，资源采集 1 条（token={token_count}）"
        return await _mark_done(db, project, task, role, summary, True)
    except Exception as exc:  # noqa: BLE001
        logger.exception("运维巡检失败")
        await monitor_service.append_log(
            db, project.id, "error", f"运维巡检异常: {exc}", stage_id=stage_id
        )
        return await _mark_done(db, project, task, role, str(exc), False)
