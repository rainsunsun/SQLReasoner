"""报告 agent：把校验后的查询结果解读成面向业务方的分析报告。"""
from __future__ import annotations

from app.agents.common import format_results
from app.llm import invoke_structured
from app.models import AnalysisGoal, AnalysisReport, QueryResult, Verification

_SYSTEM = """你是数据分析团队的报告撰写人。基于查询结果，产出一份面向业务方的分析报告。

要求：
1. answer 直接、明确地回答原始业务问题
2. key_findings 提炼 2~5 条关键发现，每条都要引用真实数字
3. evidence 说明支撑结论的数据依据（具体到数字）
4. confidence 给出 0~1 的可信度（结果完整、口径正确则高）
5. needs_review：只有结果明显异常、为空、或口径存疑时才 true，否则 false
"""


def report(
    question: str,
    goal: AnalysisGoal,
    results: list[QueryResult],
    verification: Verification,
) -> AnalysisReport:
    data = format_results(results)
    return invoke_structured(
        AnalysisReport,
        _SYSTEM,
        f"原始业务问题：{question}\n\n"
        f"分析目标：\n{goal.model_dump_json()}\n\n"
        f"查询结果：\n{data}\n\n"
        f"校验结论：passed={verification.passed}, issues={verification.issues}, note={verification.note}",
    )
