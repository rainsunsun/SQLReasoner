"""后端 API：健康检查、入参校验、两阶段 ask/review 流程（用假图，不调 LLM）。"""
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.models import AnalysisReport
from app.server import create_app


def _fake_graph(result):
    class G:
        def invoke(self, state, config):
            return result

    return G()


def test_health():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ask_empty_question_rejected():
    client = TestClient(create_app())
    resp = client.post("/ask", json={"question": ""})
    assert resp.status_code == 422


def test_ask_done():
    report = AnalysisReport(answer="PushEvent 最多", key_findings=[], evidence="", confidence=0.97)
    client = TestClient(create_app(_fake_graph({"report": report})))
    resp = client.post("/ask", json={"question": "哪种事件最多"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert body["report"]["answer"] == "PushEvent 最多"


def test_ask_review_then_resume():
    interrupt = SimpleNamespace(
        value={"question": "要复核", "answer": "x", "confidence": 0.5, "key_findings": []}
    )
    report = AnalysisReport(answer="最终结论", key_findings=[], evidence="", confidence=0.9)

    class G:
        def __init__(self):
            self.n = 0

        def invoke(self, state, config):
            self.n += 1
            return {"__interrupt__": [interrupt]} if self.n == 1 else {"report": report}

    client = TestClient(create_app(G()))
    resp = client.post("/ask", json={"question": "q"})
    body = resp.json()
    assert body["status"] == "needs_review"
    assert body["thread_id"]

    resp2 = client.post("/review", json={"thread_id": body["thread_id"], "decision": "accept"})
    body2 = resp2.json()
    assert body2["status"] == "done"
    assert body2["report"]["answer"] == "最终结论"


def test_review_invalid_decision_rejected():
    client = TestClient(create_app())
    resp = client.post("/review", json={"thread_id": "t", "decision": "maybe"})
    assert resp.status_code == 422
