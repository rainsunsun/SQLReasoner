"""编排图：能构建、路由逻辑正确（含人工复核 reject 回环与上限）。"""
import sqlite3
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.graph.workflow import _route_report, _route_review, build_graph, build_persistent_graph


def test_build_graph():
    assert build_graph() is not None


def test_build_persistent_graph(tmp_path):
    g = build_persistent_graph(tmp_path / "ckpt.sqlite")
    assert g is not None
    assert (tmp_path / "ckpt.sqlite").exists()


class _MiniState(TypedDict):
    x: int


def _build_mini(saver):
    g = StateGraph(_MiniState)
    g.add_node("a", lambda s: {"x": s.get("x", 0) + 1})
    g.add_edge(START, "a")
    g.add_edge("a", END)
    return g.compile(checkpointer=saver)


def test_persistent_checkpoint_survives_restart(tmp_path):
    """checkpoint 落盘后，新连接 + 新 saver 能读回旧状态（模拟服务重启不丢会话）。"""
    db = tmp_path / "ckpt.sqlite"
    cfg = {"configurable": {"thread_id": "t1"}}

    # 会话一：写 checkpoint（0 -> 1，再从 1 续跑 -> 2）
    mini1 = _build_mini(build_persistent_graph(db).checkpointer)
    mini1.invoke({"x": 0}, cfg)
    mini1.invoke({}, cfg)

    # 会话二：全新连接 + 全新 saver，读同一文件
    conn = sqlite3.connect(str(db), check_same_thread=False)
    mini2 = _build_mini(SqliteSaver(conn))
    assert mini2.get_state(cfg).values["x"] == 2


def test_route_report():
    assert _route_report({"needs_review": True}) == "review"
    assert _route_report({}) == END


def test_route_review():
    assert _route_review({"human_decision": "reject", "review_count": 0}) == "plan"
    assert _route_review({"human_decision": "reject", "review_count": 2}) == END
    assert _route_review({"human_decision": "accept", "review_count": 0}) == END
