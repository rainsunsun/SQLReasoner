"""规划 agent：把分析目标拆解成按顺序执行的 SQL 查询计划。"""
from __future__ import annotations

from app.llm import invoke_structured
from app.models import AnalysisGoal, QueryPlan

_SYSTEM = """你是数据分析团队的规划师。根据需求分析师给的分析目标，拆解出按顺序执行的 SQL 查询步骤。

数据表 events 结构：
- id VARCHAR
- type VARCHAR（PushEvent/IssuesEvent/PullRequestEvent/WatchEvent/ForkEvent/CreateEvent/IssueCommentEvent 等）
- actor_login VARCHAR
- repo_name VARCHAR（owner/repo 格式）
- created_at TIMESTAMP（时间戳类型，过滤/聚合直接用 created_at >= '2026-09-01 00:00:00'，无需转换）
- action VARCHAR（opened/closed/reopened 等，仅部分事件有）
- payload VARCHAR（JSON 字符串，用 json_extract_string(payload, '$.field') 解析）

要求：
1. 每个 step 的 sql 必须是只读 SELECT
2. 步骤按依赖顺序排列，但每个 SQL 各自独立（不跨步骤引用中间结果）
3. 优先用聚合函数（count/sum/avg/date_trunc）直接算出结论，减少步骤数
4. 只写对回答问题必要的 SQL，不要多余步骤
"""


def plan(goal: AnalysisGoal) -> QueryPlan:
    return invoke_structured(QueryPlan, _SYSTEM, f"分析目标：\n{goal.model_dump_json()}")
