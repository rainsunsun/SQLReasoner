"""self-repair 压力测试：对故意注入常见错误的 SQL 测修复率。

回答面试官可能的拷问：「你的 SQL 自我修复到底修复过什么？修复率多少？」

做法：8 条故意注入 LLM 常见错误的 SQL（列名/表名写错、漏引号、时间戳格式错、别名不存在等），
走 executor 的修复循环（执行失败 → 报错回流 → LLM 结构化修正 → 重跑，上限 3 次），
统计修复成功率。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app import config
from app.agents.executor import _fix_sql
from app.models import QueryStep
from app.tools.db import execute_sql

# (故意注入错误的 SQL, 错误类型说明)
BROKEN: list[tuple[str, str]] = [
    ("SELECT event_type, count(*) c FROM events GROUP BY event_type ORDER BY c DESC LIMIT 1", "列名 event_type→type"),
    ("SELECT count(*) FROM github_events", "表名 github_events→events"),
    ("SELECT count(*) FROM events WHERE type = PushEvent", "字符串漏引号"),
    ("SELECT repo, count(*) c FROM events GROUP BY repo ORDER BY c DESC LIMIT 1", "列名 repo→repo_name"),
    ("SELECT actor, count(*) c FROM events GROUP BY actor ORDER BY c DESC LIMIT 1", "列名 actor→actor_login"),
    ("SELECT count(*) FROM events WHERE created_at > '2026-09-01 01:00:00:00'", "时间戳格式错误"),
    ("SELECT type, count(*) FROM events GROUP BY type ORDER BY cnt DESC LIMIT 3", "引用不存在的别名 cnt"),
    ("SELECT count(*) FROM events WHERE type IN (PushEvent, IssuesEvent)", "IN 里漏引号"),
]


def repair(sql: str, desc: str) -> tuple[bool, str]:
    for attempt in range(config.MAX_RETRY + 1):
        res = execute_sql(sql)
        if res.success:
            return True, sql
        if attempt < config.MAX_RETRY:
            sql = _fix_sql(QueryStep(step=1, purpose=desc, sql=sql), res.error)
    return False, sql


if __name__ == "__main__":
    ok = 0
    print(f"MAX_RETRY = {config.MAX_RETRY}\n")
    for sql, desc in BROKEN:
        fixed, final = repair(sql, desc)
        print(f"{'✓' if fixed else '✗'} [{desc}] → {final[:80]}")
        ok += fixed
    print(f"\nself-repair 修复率：{ok}/{len(BROKEN)}")
