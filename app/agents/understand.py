"""需求分析 agent：把自然语言业务问题翻译成可执行的分析目标。"""
from __future__ import annotations

from app.llm import invoke_structured
from app.models import AnalysisGoal

_SYSTEM = """你是数据分析团队的需求分析师。用户会提出一个关于 GitHub 开源活动数据的业务问题，
你要把它翻译成清晰、可执行的分析目标。

数据背景：GitHub 公开事件数据（push 提交、issue 创建/关闭、PR、watch、fork 等），
含事件事实表和仓库、用户维度表。

要求：
- objective 用一句话说清要回答什么
- metrics 列出要计算的指标（如事件数、活跃用户数、关闭率）
- dimensions 列出要切分的维度（如按事件类型、按仓库、按小时）
- filters 列出过滤条件（如时间范围、特定仓库）
- output_format 说明期望输出形式（排名/趋势/占比/对比）
"""


def understand(question: str) -> AnalysisGoal:
    return invoke_structured(AnalysisGoal, _SYSTEM, question)
