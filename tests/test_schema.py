"""schema 工具：从真实库动态读表结构，替代硬编码。"""
import duckdb

from app.tools.schema import get_schema_text


def test_get_schema_text(tmp_path):
    db = tmp_path / "t.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE events (id VARCHAR, type VARCHAR, actor_login VARCHAR)")
    con.execute("CREATE TABLE repos (name VARCHAR, owner VARCHAR)")
    con.execute("CREATE TABLE actors (login VARCHAR)")
    con.close()

    text = get_schema_text(db)
    assert "events" in text and "actor_login" in text
    assert "repos" in text and "owner" in text
    assert "actors" in text
    assert "join" in text          # 表间关联提示
    assert "事件事实表" in text     # 中文描述来自元数据


def test_get_schema_text_empty(tmp_path):
    db = tmp_path / "empty.duckdb"
    duckdb.connect(str(db)).close()
    assert "没有可用的表" in get_schema_text(db)
