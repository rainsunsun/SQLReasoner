"""规划 agent：根据 schema linking 精选的表列，拆解出按顺序执行的 SQL 查询计划。"""
from __future__ import annotations

from app.llm import invoke_structured
from app.models import AnalysisGoal, LinkedSchema, QueryPlan

_SYSTEM = """你是数据分析团队的规划师。根据需求分析师给的分析目标、以及 schema linking 精选的相关表列，拆解出按顺序执行的 SQL 查询步骤。

要求：
1. 每个 step 的 sql 必须是只读 SELECT
2. 只使用「相关表列」里给出的表和列，不要引用不存在的列
3. 步骤按依赖顺序排列，但每个 SQL 各自独立（不跨步骤引用中间结果）
4. 优先用聚合函数（count/sum/avg/date_trunc）直接算出结论，减少步骤数
5. 多表查询时用给出的 join 关系关联；只写对回答问题必要的 SQL，不要多余步骤
"""


def _format_linked(linked: LinkedSchema) -> str:
    blocks = [f"表 {t.table}（列：{', '.join(t.columns)}）—— {t.reason}" for t in linked.tables]
    if linked.join_hints:
        blocks.append("join 关系：" + "；".join(linked.join_hints))
    return "\n".join(blocks)


def plan(goal: AnalysisGoal, linked: LinkedSchema) -> QueryPlan:
    human = (
        f"分析目标：\n{goal.model_dump_json()}\n\n"
        f"相关表列（schema linking 结果）：\n{_format_linked(linked)}"
    )
    return invoke_structured(QueryPlan, _SYSTEM, human)
