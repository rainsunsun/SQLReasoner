"""LangGraph SOP 编排：把 5 个 agent 串成数据分析流水线。

拓扑：understand -> plan -> execute -> verify -> report -> (人工复核?) -> END
      人工复核时若拒绝，则回到 plan 重新规划+执行+校验+报告（带次数上限防死循环）。

类比 MetaGPT 的 SOP：每个 agent 职责单一，通过共享 state（类比消息池）传递
「问题 -> 分析目标 -> 查询计划 -> 查询结果 -> 校验 -> 报告」。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents import executor, linker, planner, reporter, understand, verifier
from app.config import CHECKPOINT_PATH
from app.state import AnalystState
from app.tools.schema import get_schema_text


def _understand_node(state: AnalystState) -> dict:
    return {"goal": understand.understand(state["question"])}


def _link_node(state: AnalystState) -> dict:
    """schema linking：按问题精筛相关表列，只把必需 schema 交给规划 agent。"""
    schema_text = get_schema_text()
    return {"linked_schema": linker.link(state["question"], state["goal"], schema_text)}


def _plan_node(state: AnalystState) -> dict:
    return {"plan": planner.plan(state["goal"], state["linked_schema"])}


def _execute_node(state: AnalystState) -> dict:
    return {"results": executor.execute(state["plan"])}


def _verify_node(state: AnalystState) -> dict:
    return {"verification": verifier.verify(state["goal"], state["results"])}


def _report_node(state: AnalystState) -> dict:
    v = state["verification"]
    rep = reporter.report(state["question"], state["goal"], state["results"], v)
    # 报告自己判定需复核，或校验没通过 -> 都要人工兜底
    return {"report": rep, "needs_review": rep.needs_review or not v.passed}


def _route_report(state: AnalystState) -> str:
    return "review" if state.get("needs_review") else END


_MAX_REVIEW = 2  # 最多重新分析次数：人工连续拒绝 2 次后强制结束，防死循环


def _review_node(state: AnalystState) -> dict:
    """human-in-the-loop：结论存疑时中断交人工确认；拒绝则记录并回到 plan 重跑。"""
    rep = state["report"]
    answer = interrupt(
        {
            "question": "分析报告需要人工复核，请决定：接受结论 还是 重新分析？",
            "answer": rep.answer,
            "confidence": round(rep.confidence, 2),
            "key_findings": rep.key_findings,
        }
    )
    review_count = state.get("review_count", 0) + (1 if answer == "reject" else 0)
    return {
        "report": rep.model_copy(update={"needs_review": False}),
        "human_decision": answer,
        "review_count": review_count,
    }


def _route_review(state: AnalystState) -> str:
    """人工拒绝且未超上限 → 回 plan 重新分析；接受或超限 → 结束。"""
    if state.get("human_decision") == "reject" and state.get("review_count", 0) < _MAX_REVIEW:
        return "plan"
    return END


def build_graph(checkpointer=None):
    """构建流水线图。默认用内存 checkpoint（单次运行/测试），可注入任意 checkpointer。"""
    g = StateGraph(AnalystState)
    g.add_node("understand", _understand_node)
    g.add_node("link", _link_node)
    g.add_node("plan", _plan_node)
    g.add_node("execute", _execute_node)
    g.add_node("verify", _verify_node)
    g.add_node("report", _report_node)
    g.add_node("review", _review_node)

    g.add_edge(START, "understand")
    g.add_edge("understand", "link")
    g.add_edge("link", "plan")
    g.add_edge("plan", "execute")
    g.add_edge("execute", "verify")
    g.add_edge("verify", "report")
    g.add_conditional_edges("report", _route_report, {"review": "review", END: END})
    g.add_conditional_edges("review", _route_review, {"plan": "plan", END: END})

    return g.compile(checkpointer=checkpointer or MemorySaver())


def build_persistent_graph(db_path: str | Path | None = None):
    """SQLite 持久化 checkpoint：会话状态落盘，服务重启 / 多实例不丢。"""
    target = Path(db_path) if db_path is not None else CHECKPOINT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False：FastAPI 线程池里不同线程共享连接；checkpoint 表由 saver 懒建
    conn = sqlite3.connect(str(target), check_same_thread=False)
    return build_graph(checkpointer=SqliteSaver(conn))
