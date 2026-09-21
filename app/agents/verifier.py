"""校验 agent：检查查询结果是否合理、口径是否正确。"""
from __future__ import annotations

from app.agents.common import format_results
from app.llm import get_llm
from app.models import AnalysisGoal, QueryResult, Verification

_SYSTEM = """你是数据分析团队的质检员。请校验查询结果是否合理、口径是否正确。

重点检查：
1. 结果是否为空（可能是查询条件太严或字段拼错）
2. 数字量级是否合理（事件数是否异常偏大/偏小）
3. 是否真的回答了分析目标
4. 多个步骤之间结果是否自洽

只针对明显问题报错，不要吹毛求疵；结果正常就 passed=true 并简要说明。
"""


def verify(goal: AnalysisGoal, results: list[QueryResult]) -> Verification:
    llm = get_llm().with_structured_output(Verification, method="function_calling")
    data = format_results(results)
    return llm.invoke(
        [
            ("system", _SYSTEM),
            ("human", f"分析目标：\n{goal.model_dump_json()}\n\n查询结果：\n{data}"),
        ]
    )
