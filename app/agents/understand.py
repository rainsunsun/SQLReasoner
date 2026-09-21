"""需求分析 agent：把自然语言业务问题翻译成可执行的分析目标。"""
from __future__ import annotations

from app.llm import get_llm
from app.models import AnalysisGoal

_SYSTEM = """你是数据分析团队的需求分析师。用户会提出一个关于 GitHub 开源活动数据的业务问题，
你要把它翻译成清晰、可执行的分析目标。

数据背景：一张 events 表，记录 GitHub 公开事件（push 提交、issue 创建/关闭、PR、watch、fork 等），
字段：id, type(事件类型), actor_login(用户名), repo_name(仓库名), created_at(时间), action(动作), payload(载荷JSON)。

要求：
- objective 用一句话说清要回答什么
- metrics 列出要计算的指标（如事件数、活跃用户数、关闭率）
- dimensions 列出要切分的维度（如按事件类型、按仓库、按小时）
- filters 列出过滤条件（如时间范围、特定仓库）
- output_format 说明期望输出形式（排名/趋势/占比/对比）
"""


def understand(question: str) -> AnalysisGoal:
    llm = get_llm().with_structured_output(AnalysisGoal, method="function_calling")
    return llm.invoke([("system", _SYSTEM), ("human", question)])
