"""动态 schema 读取：从 DuckDB information_schema 读真实表结构（单一事实来源）。

替代硬编码：agent 不再把表结构写死在 prompt 里，而是运行时从库里读，
schema 变更（加表/改列/重命名）自动生效，无需改 prompt 代码。

中文语义描述单独维护在 TABLE_DESCRIPTIONS / COLUMN_DESCRIPTIONS / JOIN_HINTS，
因为 DuckDB 原生表注释缺省，这里补足业务语义供 linker/planner 理解列含义。
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from app.config import DB_PATH

logger = logging.getLogger(__name__)

TABLE_DESCRIPTIONS: dict[str, str] = {
    "events": "GitHub 事件事实表：每行一条公开事件（push/issue/PR/watch 等）",
    "repos": "仓库维度表：repo_name 去重，拆出 owner/repo",
    "actors": "用户维度表：actor_login 去重",
}

COLUMN_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "events": {
        "id": "事件唯一 ID",
        "type": "事件类型（PushEvent/IssuesEvent/PullRequestEvent/WatchEvent/ForkEvent 等）",
        "actor_login": "触发事件的用户名",
        "repo_name": "仓库名（owner/repo 格式）",
        "created_at": "事件发生时间（TIMESTAMP，过滤直接用 created_at >= '...'）",
        "action": "动作（opened/closed/merged/labeled 等，仅部分事件有）",
        "payload": "事件载荷（JSON 字符串，用 json_extract_string(payload, '$.field') 解析）",
    },
    "repos": {
        "name": "仓库名（owner/repo）",
        "owner": "仓库所有者（组织或个人）",
        "repo": "仓库名（不含 owner 部分）",
    },
    "actors": {
        "login": "用户名",
    },
}

JOIN_HINTS: list[str] = [
    "events.repo_name = repos.name（事件 → 仓库，按仓库/owner 聚合时 join）",
    "events.actor_login = actors.login（事件 → 用户，按用户聚合时 join）",
]


def _describe(table: str, column: str, col_type: str) -> str:
    desc = COLUMN_DESCRIPTIONS.get(table, {}).get(column, "")
    return f"- {column} {col_type}：{desc}" if desc else f"- {column} {col_type}"


def get_schema_text(db_path: str | Path | None = None) -> str:
    """读真实表结构，返回带中文描述的可读文本（供 linker/planner prompt 注入）。"""
    target = Path(db_path) if db_path is not None else DB_PATH
    with duckdb.connect(str(target), read_only=True) as con:
        rows = con.execute(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'main'
            ORDER BY table_name, ordinal_position
            """
        ).fetchall()

    if not rows:
        logger.warning("数据库里没有任何表：%s", target)
        return "（数据库为空，没有可用的表）"

    by_table: dict[str, list[tuple[str, str]]] = {}
    for table, column, col_type in rows:
        by_table.setdefault(table, []).append((column, col_type))

    blocks: list[str] = []
    for table, cols in by_table.items():
        title = TABLE_DESCRIPTIONS.get(table, table)
        lines = [f"表 {table}（{title}）："]
        lines.extend(_describe(table, c, t) for c, t in cols)
        blocks.append("\n".join(lines))

    if JOIN_HINTS:
        blocks.append("表间关联（join 条件）：\n" + "\n".join(f"- {h}" for h in JOIN_HINTS))
    return "\n\n".join(blocks)
