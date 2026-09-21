"""评估集：12 个针对 GitHub 事件数据的真实分析问题，答案均为预先算好的确定值。

覆盖的分析类型：Top-N、总量、去重计数、时间范围过滤、按小时聚合、多类型求和、
按实体聚合（仓库/用户）、payload action 解析、特定类型计数。

判题方式（确定性、可复现，不引入 LLM 判题 bias）：
- keys 是「答案必须包含的关键事实」（实体 + 精确数字）
- 归一化（去大小写/空格/逗号/标点）后，检查每个 key 是否都出现在系统 answer 中
- 数据分析场景要求精确数字，所以用精确数字判题（「大概 10 万」不算对）

ref_sql 为人工写的参考查询，用于说明口径与复现 ground truth。
"""
from __future__ import annotations

QUESTIONS: list[dict] = [
    {
        "id": "q01",
        "question": "2026-09-01 00:00 到 02:00 这两个小时，GitHub 上哪种事件类型最多？有多少条？",
        "ref_sql": (
            "SELECT type, count(*) c FROM events "
            "WHERE created_at >= '2026-09-01 00:00:00' AND created_at < '2026-09-01 02:00:00' "
            "GROUP BY type ORDER BY c DESC LIMIT 1"
        ),
        "keys": ["pushevent", "104834"],
    },
    {
        "id": "q02",
        "question": "2026-09-01 00:00 到 02:00 这两个小时里，GitHub 一共记录了多少条事件？",
        "ref_sql": "SELECT count(*) FROM events",
        "keys": ["108537"],
    },
    {
        "id": "q03",
        "question": "事件类型第二多的是哪种？有多少条？",
        "ref_sql": "SELECT type, count(*) c FROM events GROUP BY type ORDER BY c DESC LIMIT 1 OFFSET 1",
        "keys": ["createevent", "1765"],
    },
    {
        "id": "q04",
        "question": "这两个小时里一共有多少种不同的事件类型？",
        "ref_sql": "SELECT count(DISTINCT type) FROM events",
        "keys": ["14"],
    },
    {
        "id": "q05",
        "question": "01:00 到 02:00 这一个小时里有多少条事件？",
        "ref_sql": (
            "SELECT count(*) FROM events "
            "WHERE created_at >= '2026-09-01 01:00:00' AND created_at < '2026-09-01 02:00:00'"
        ),
        "keys": ["56955"],
    },
    {
        "id": "q06",
        "question": "PullRequestEvent 和 IssuesEvent 这两种事件加起来有多少条？",
        "ref_sql": "SELECT count(*) FROM events WHERE type IN ('PullRequestEvent','IssuesEvent')",
        "keys": ["611"],
    },
    {
        "id": "q07",
        "question": "00:30 到 01:00 这半个小时里有多少条事件？",
        "ref_sql": (
            "SELECT count(*) FROM events "
            "WHERE created_at >= '2026-09-01 00:30:00' AND created_at < '2026-09-01 01:00:00'"
        ),
        "keys": ["16401"],
    },
    {
        "id": "q08",
        "question": "哪个仓库的事件最多？这个仓库有多少条事件？",
        "ref_sql": "SELECT repo_name, count(*) c FROM events GROUP BY repo_name ORDER BY c DESC LIMIT 1",
        "keys": ["trieu1082", "dbbackup", "117"],
    },
    {
        "id": "q09",
        "question": "哪个 GitHub 用户触发的事件最多？有多少条？",
        "ref_sql": "SELECT actor_login, count(*) c FROM events GROUP BY actor_login ORDER BY c DESC LIMIT 1",
        "keys": ["githubactions", "3207"],
    },
    {
        "id": "q10",
        "question": "在 IssuesEvent 里，哪种 action 出现最多？有多少条？",
        "ref_sql": (
            "SELECT action, count(*) c FROM events WHERE type='IssuesEvent' "
            "GROUP BY action ORDER BY c DESC LIMIT 1"
        ),
        "keys": ["labeled", "55"],
    },
    {
        "id": "q11",
        "question": "在 PullRequestEvent 里，merged 这个动作有多少条？",
        "ref_sql": "SELECT count(*) FROM events WHERE type='PullRequestEvent' AND action='merged'",
        "keys": ["merged", "135"],
    },
    {
        "id": "q12",
        "question": "WatchEvent 有多少条？",
        "ref_sql": "SELECT count(*) FROM events WHERE type='WatchEvent'",
        "keys": ["watchevent", "108"],
    },
]
