"""查询工具：真实执行 DuckDB SQL（供执行 agent 直接调用）。

核心魔改点：LLM 生成的 SQL 在这里被「真执行」，查出的真实数据回流，
报错也会原样返回，让 LLM 据此自我修正（自我修复循环）。不经过 LLM 的字符串中转，
执行 agent 拿到的就是结构化结果（列名 + 行数据 + 行数）。
"""
from __future__ import annotations

import duckdb

from app import config


class SqlResult:
    """结构化查询结果，供执行 agent 解析。"""

    def __init__(self, success: bool, cols: list[str], rows: list, row_count: int, error: str = ""):
        self.success = success
        self.cols = cols
        self.rows = rows
        self.row_count = row_count
        self.error = error


def execute_sql(query: str) -> SqlResult:
    """真实执行 SQL，返回结构化结果。只读连接，写操作会被 DuckDB 拒绝。"""
    con = duckdb.connect(str(config.DB_PATH), read_only=True)
    try:
        result = con.execute(query).fetchall()
        cols = [d[0] for d in con.description]
        return SqlResult(True, cols, result, len(result))
    except Exception as e:  # noqa: BLE001
        return SqlResult(False, [], [], 0, f"{type(e).__name__}: {e}")
    finally:
        con.close()
