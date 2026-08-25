"""报告服务：Markdown 权威 + HTML 派生（经 nh3 净化）+ 落盘。

对齐 SPEC §1.2.8（Q-10：Markdown 权威、HTML 派生）与《安全规范》§2.4
（报告内容含被评估源码片段与 LLM 生成文本，HTML 派生前必须 nh3 净化）。
"""

import asyncio

import aiofiles
import markdown
import nh3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import NotFoundError
from app.models.report import Report

# 允许的 HTML 标签/属性/URL scheme（安全规范 §2.4.1）
ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "ul", "ol", "li", "code", "pre", "blockquote",
    "table", "thead", "tbody", "tr", "th", "td",
    "strong", "em", "a", "hr", "br", "span",
}
ALLOWED_ATTRS = {
    "a": {"href", "title"},
    "code": {"class"},
    "span": {"class"},
}


def markdown_to_html(markdown_text: str) -> str:
    """将 Markdown 转为净化后的 HTML。

    Args:
        markdown_text: 权威 Markdown 文本。

    Returns:
        经 nh3 净化的 HTML 字符串（仅白名单标签/属性/协议）。
    """
    raw_html = markdown.markdown(
        markdown_text, extensions=["fenced_code", "tables"]
    )
    return nh3.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer",
    )


async def _upsert_report(
    db: AsyncSession, project_id: int, markdown_text: str, html_text: str, file_path: str
) -> Report:
    """插入或更新项目报告（每项目一份权威报告）。"""
    row = await db.scalar(select(Report).where(Report.project_id == project_id))
    if row is None:
        row = Report(project_id=project_id)
        db.add(row)
    row.report_markdown = markdown_text
    row.report_html = html_text
    row.report_file_path = file_path
    await db.flush()
    return row


async def generate_and_save(
    db: AsyncSession, project_id: int, markdown_text: str
) -> Report:
    """生成 HTML（nh3 净化）并落盘 Markdown 文件，再持久化报告。

    Args:
        db: 数据库会话。
        project_id: 项目 ID。
        markdown_text: 权威 Markdown 报告文本。

    Returns:
        持久化后的 Report 实例。
    """
    html_text = await asyncio.to_thread(markdown_to_html, markdown_text)
    file_path = settings.report_path / str(project_id) / f"report-{project_id}.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(file_path, "w", encoding="utf-8") as handle:
        await handle.write(markdown_text)
    return await _upsert_report(db, project_id, markdown_text, html_text, str(file_path))


async def get_report(db: AsyncSession, project_id: int) -> Report:
    """查询项目报告。

    Raises:
        NotFoundError: 报告尚未生成。
    """
    row = await db.scalar(select(Report).where(Report.project_id == project_id))
    if row is None:
        raise NotFoundError("报告不存在")
    return row
