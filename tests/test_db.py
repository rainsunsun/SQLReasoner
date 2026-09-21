"""查询工具：真执行、写操作拒绝、多语句拒绝、报错结构化返回。"""
import duckdb
import pytest

from app.tools.db import execute_sql


@pytest.fixture
def db_path(tmp_path):
    p = tmp_path / "test.duckdb"
    con = duckdb.connect(str(p))
    con.execute("CREATE TABLE events (id INTEGER, type VARCHAR)")
    con.execute("INSERT INTO events VALUES (1, 'PushEvent'), (2, 'PushEvent'), (3, 'IssuesEvent')")
    con.close()
    return p


def test_select_ok(db_path):
    res = execute_sql(
        "SELECT type, count(*) c FROM events GROUP BY type ORDER BY c DESC", db_path=db_path
    )
    assert res.success
    assert res.cols == ["type", "c"]
    assert res.row_count == 2


def test_trailing_semicolon_allowed(db_path):
    res = execute_sql("SELECT count(*) FROM events;", db_path=db_path)
    assert res.success
    assert res.row_count == 1


def test_write_rejected(db_path):
    res = execute_sql("DROP TABLE events", db_path=db_path)
    assert not res.success
    assert "拒绝" in res.error


def test_multi_statement_rejected(db_path):
    res = execute_sql("SELECT 1; SELECT 2", db_path=db_path)
    assert not res.success


def test_bad_column_returns_failure(db_path):
    res = execute_sql("SELECT nonexistent_col FROM events", db_path=db_path)
    assert not res.success
    assert res.error


def test_empty_query_rejected(db_path):
    res = execute_sql("   ", db_path=db_path)
    assert not res.success
