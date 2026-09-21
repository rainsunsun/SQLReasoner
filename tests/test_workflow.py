"""编排图：能构建、路由逻辑正确（含人工复核 reject 回环与上限）。"""
from langgraph.graph import END

from app.graph.workflow import _route_report, _route_review, build_graph


def test_build_graph():
    assert build_graph() is not None


def test_route_report():
    assert _route_report({"needs_review": True}) == "review"
    assert _route_report({}) == END


def test_route_review():
    assert _route_review({"human_decision": "reject", "review_count": 0}) == "plan"
    assert _route_review({"human_decision": "reject", "review_count": 2}) == END
    assert _route_review({"human_decision": "accept", "review_count": 0}) == END
