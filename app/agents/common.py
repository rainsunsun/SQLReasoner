"""agent 间共享的小工具函数。"""
from __future__ import annotations

from app.models import QueryResult


def format_results(results: list[QueryResult], max_rows: int = 50) -> str:
    """把查询结果列表格式化成文本，供校验/报告 agent 阅读。"""
    blocks: list[str] = []
    for r in results:
        blocks.append(f"--- 步骤 {r.step}：{'成功' if r.success else '失败'} ---")
        blocks.append(f"SQL: {r.sql}")
        if not r.success:
            blocks.append(f"错误: {r.error}")
            continue
        if not r.rows:
            blocks.append("(空结果)")
            continue
        cols = list(r.rows[0].keys())
        blocks.append(" | ".join(cols))
        for row in r.rows[:max_rows]:
            blocks.append(" | ".join("" if row[c] is None else str(row[c]) for c in cols))
        if r.row_count > max_rows:
            blocks.append(f"(共 {r.row_count} 行，仅显示前 {max_rows} 行)")
    return "\n".join(blocks)
