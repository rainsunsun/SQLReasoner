"""查询工具：真实执行 DuckDB SQL（供执行 agent 直接调用）。

核心魔改点：LLM 生成的 SQL 在这里被「真执行」，查出的真实数据结构化回流，
报错原样返回，让 LLM 据此自我修正（self-repair 循环）。不经过 LLM 字符串中转。

稳健性：
- read_only=True：写操作被 DuckDB 直接拒绝（代码层兜底）
- 白名单校验：只放行单条只读 SELECT/WITH，拒绝写语句与多语句注入
- 上下文管理器：连接无论成败一定关闭，不泄漏
- db_path 可注入：单测可用临时库，不依赖真实数据
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from app.config import DB_PATH

logger = logging.getLogger(__name__)

# 写操作开头关键词（大小写不敏感）：只读查询一律拒绝，防御性拦截 + 更清晰的报错
_WRITE_PREFIXES = {
    "insert", "update", "delete", "create", "drop", "alter", "truncate",
    "grant", "revoke", "merge", "copy", "attach", "detach", "pragma",
    "set", "call", "begin", "commit", "rollback", "vacuum", "export",
    "import", "install", "load", "checkpoint",
}


class SqlResult:
    """结构化查询结果，供执行 agent 解析。"""

    def __init__(self, success: bool, cols: list[str], rows: list, row_count: int, error: str = ""):
        self.success = success
        self.cols = cols
        self.rows = rows
        self.row_count = row_count
        self.error = error

    def __repr__(self) -> str:
        state = "成功" if self.success else "失败"
        return f"<SqlResult {state} rows={self.row_count}>"


def _validate_query(query: str) -> str | None:
    """校验 SQL：只放行单条只读查询。返回 None 表示合法，否则返回错误说明。"""
    stripped = query.strip()
    if not stripped:
        return "SQL 为空"
    if stripped.endswith(";"):
        stripped = stripped[:-1].strip()
    if ";" in stripped:
        return "不允许包含多条语句（分号分隔）"
    head = stripped.split(None, 1)[0].lower()
    if head in _WRITE_PREFIXES:
        return f"只允许只读查询，拒绝写操作（{head.upper()}）"
    if head not in ("select", "with"):
        return f"只允许 SELECT/WITH 只读查询，收到以 {head.upper()} 开头的语句"
    return None


def execute_sql(query: str, db_path: str | Path | None = None) -> SqlResult:
    """真实执行 SQL，返回结构化结果。只读连接 + 白名单校验。"""
    err = _validate_query(query)
    if err:
        return SqlResult(False, [], [], 0, err)

    target = Path(db_path) if db_path is not None else DB_PATH
    try:
        with duckdb.connect(str(target), read_only=True) as con:
            con.execute(query)
            cols = [d[0] for d in con.description] if con.description else []
            rows = con.fetchall()
    except Exception as e:  # noqa: BLE001
        logger.warning("SQL 执行失败：%s", e)
        return SqlResult(False, [], [], 0, f"{type(e).__name__}: {e}")

    return SqlResult(True, cols, rows, len(rows))
