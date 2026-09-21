"""执行 agent：真实执行查询计划里的 SQL，失败时让 LLM 根据报错自我修正。

这是「真执行去 toy 化」的核心：SQL 不是 LLM 口头说说，而是真的查库；
查出的真实数据回流；报错时 LLM 看错误信息修正 SQL 重跑（自我修复循环）。
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import settings
from app.llm import invoke_structured
from app.models import QueryPlan, QueryResult, QueryStep
from app.tools.db import execute_sql


class _FixedSQL(BaseModel):
    """LLM 修正 SQL 的结构化输出。"""

    sql: str = Field(description="修正后的 SQL")
    reason: str = Field(description="修正原因")


_FIX_SYSTEM = """你是 SQL 修正专家。下面有一条执行失败的 SQL 和报错信息，请修正它。

数据表 events 结构：
- id VARCHAR, type VARCHAR, actor_login VARCHAR, repo_name VARCHAR
- created_at TIMESTAMP（时间戳类型，过滤直接用 created_at >= '2026-09-01 00:00:00'）
- action VARCHAR, payload VARCHAR（JSON 字符串）

修正要求：
1. 只输出能修复报错的 SQL，保持原有分析意图不变
2. 字段名/语法错误就改正；类型问题就加正确的 CAST
3. 不要改成与原意图无关的查询
"""


def _fix_sql(step: QueryStep, error: str) -> str:
    out = invoke_structured(
        _FixedSQL,
        _FIX_SYSTEM,
        f"原 SQL：\n{step.sql}\n\n报错：\n{error}",
    )
    return out.sql


def execute(plan: QueryPlan) -> list[QueryResult]:
    results: list[QueryResult] = []
    for step in plan.steps:
        sql = step.sql
        result: QueryResult | None = None
        for attempt in range(settings.max_retry + 1):
            res = execute_sql(sql)
            if res.success:
                rows = [dict(zip(res.cols, row, strict=True)) for row in res.rows]
                result = QueryResult(
                    step=step.step, sql=sql, success=True, rows=rows, row_count=res.row_count
                )
                break
            if attempt < settings.max_retry:
                sql = _fix_sql(step, res.error)  # 让 LLM 看报错自我修正
            else:
                result = QueryResult(step=step.step, sql=sql, success=False, error=res.error)
        assert result is not None
        results.append(result)
    return results
