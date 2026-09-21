"""FastAPI 后端：把 CLI 的 human-in-the-loop 变成真正的 HTTP 两阶段服务。

- POST /ask     提交问题 → 跑到「完成」或「触发人工复核」就返回
- POST /review  对已复核的 thread 下发 accept/reject，恢复 interrupt 继续跑
- GET  /health  健康检查

线程隔离用 thread_id：每个 thread 对应一次独立对话的 checkpoint 状态。
启动：uvicorn app.server:app --reload
"""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, HTTPException
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.graph.workflow import build_graph
from app.models import AnalysisReport

logger = logging.getLogger(__name__)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, description="要分析的业务问题")
    thread_id: str | None = Field(default=None, description="会话 ID，不传则新建")


class ReviewRequest(BaseModel):
    thread_id: str = Field(description="要复核的会话 ID")
    decision: str = Field(pattern="^(accept|reject)$", description="accept 接受 / reject 重新分析")


class AskResponse(BaseModel):
    thread_id: str
    status: str  # done | needs_review
    report: AnalysisReport | None = None
    review: dict | None = None


def _invoke(graph, state, config) -> tuple[dict, str, dict | None]:
    """跑图，直到完成或中断；返回 (result, status, 复核载荷)。"""
    result = graph.invoke(state, config)
    if "__interrupt__" in result:
        return result, "needs_review", result["__interrupt__"][0].value
    return result, "done", None


def create_app(graph=None) -> FastAPI:
    app = FastAPI(title="SQLReasoner", version="0.1.0")
    g = graph if graph is not None else build_graph()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/ask", response_model=AskResponse)
    def ask(req: AskRequest) -> AskResponse:
        thread_id = req.thread_id or uuid.uuid4().hex
        config = {"configurable": {"thread_id": thread_id}}
        try:
            result, status, review = _invoke(g, {"question": req.question}, config)
        except Exception as e:  # noqa: BLE001
            logger.exception("分析失败")
            raise HTTPException(status_code=500, detail=f"分析失败：{e}") from e
        return AskResponse(
            thread_id=thread_id,
            status=status,
            report=result.get("report") if status == "done" else None,
            review=review,
        )

    @app.post("/review", response_model=AskResponse)
    def review(req: ReviewRequest) -> AskResponse:
        config = {"configurable": {"thread_id": req.thread_id}}
        try:
            result, status, review = _invoke(g, Command(resume=req.decision), config)
        except Exception as e:  # noqa: BLE001
            logger.exception("复核恢复失败")
            raise HTTPException(status_code=500, detail=f"恢复失败：{e}") from e
        return AskResponse(
            thread_id=req.thread_id,
            status=status,
            report=result.get("report") if status == "done" else None,
            review=review,
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.server:app", host="127.0.0.1", port=8000, reload=True)
