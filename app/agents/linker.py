"""schema linking agent：把业务问题映射到相关的表和列子集。

这是 Text-to-SQL 里防幻觉的关键一步：不把全量 schema 一股脑塞给规划 agent，
而是先根据问题精筛出「必需的列 + 表间 join 关系」，再让规划 agent 写 SQL。
"""
from __future__ import annotations

from app.llm import invoke_structured
from app.models import AnalysisGoal, LinkedSchema

_SYSTEM = """你是 schema linking 专家。给定业务问题和完整数据 schema，找出回答问题必需的表和列。

要求：
1. 只选回答问题必需的列，宁少勿多——无关列会干扰后续 SQL 生成
2. 涉及多表时（如「哪个仓库的 owner 最活跃」），把相关表都选上，并在 join_hints 说明关联条件
3. 时间、事件类型、用户名、仓库名这类过滤/分组字段若问题提到就一定要选上
4. columns 填真实的列名（必须来自给出的 schema，不能自己编造）
"""


def link(question: str, goal: AnalysisGoal, schema_text: str) -> LinkedSchema:
    human = (
        f"业务问题：{question}\n\n"
        f"分析目标：\n{goal.model_dump_json()}\n\n"
        f"完整数据 schema：\n{schema_text}"
    )
    return invoke_structured(LinkedSchema, _SYSTEM, human)
