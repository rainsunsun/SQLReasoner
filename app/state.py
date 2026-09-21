"""LangGraph 状态：贯穿整个 SOP 流水线的共享上下文（类比 MetaGPT 的消息池）。"""
from __future__ import annotations

from typing import TypedDict

from app.models import AnalysisGoal, AnalysisReport, QueryPlan, QueryResult, Verification


class AnalystState(TypedDict, total=False):
    question: str                       # 用户原始业务问题
    goal: AnalysisGoal                  # 需求分析结果
    plan: QueryPlan                     # 查询计划
    results: list[QueryResult]          # 查询结果（真实数据，可能多步）
    verification: Verification          # 校验结果
    report: AnalysisReport              # 最终报告
    needs_review: bool                  # 是否触发人工复核
    human_decision: str                 # 人工复核决定：accept / reject
    review_count: int                   # 已重新分析的次数（防死循环）
