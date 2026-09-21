"""领域模型：既是分析流水线各阶段的产出，也是 LLM 结构化输出 schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisGoal(BaseModel):
    """需求分析 agent 的输出：把业务问题翻译成可执行的分析目标。"""

    objective: str = Field(description="分析目标，一句话说清要回答什么")
    metrics: list[str] = Field(description="要计算的指标，如提交次数/关闭时长")
    dimensions: list[str] = Field(description="要切分的维度，如按作者/按仓库/按时间")
    filters: list[str] = Field(description="过滤条件，如时间范围/仓库名")
    output_format: str = Field(description="期望输出形式：表格/趋势/对比/排名")


class QueryStep(BaseModel):
    """规划 agent 输出的单个查询步骤。"""

    step: int = Field(description="步骤序号，从 1 开始")
    purpose: str = Field(description="这一步要回答什么子问题")
    sql: str = Field(description="要执行的 SQL（只读 SELECT）")


class QueryPlan(BaseModel):
    """规划 agent 的输出：完整的查询计划。"""

    steps: list[QueryStep] = Field(description="按顺序执行的查询步骤")


class QueryResult(BaseModel):
    """执行 agent 返回的单步查询结果（真实数据回流）。"""

    step: int = Field(description="步骤序号")
    sql: str = Field(description="实际执行的 SQL")
    success: bool = Field(description="是否执行成功")
    rows: list[dict] = Field(default_factory=list, description="结果行（真实数据）")
    row_count: int = Field(default=0, description="结果行数")
    error: str = Field(default="", description="失败时的错误信息")


class Verification(BaseModel):
    """校验 agent 的输出：检查结果合理性。"""

    passed: bool = Field(description="结果是否可信")
    issues: list[str] = Field(default_factory=list, description="发现的问题")
    note: str = Field(default="", description="校验说明")


class AnalysisReport(BaseModel):
    """报告 agent 的输出：面向业务方的最终结论。"""

    answer: str = Field(description="直接回答原始业务问题")
    key_findings: list[str] = Field(description="关键发现")
    evidence: str = Field(description="支撑结论的数据依据（引用真实数字）")
    confidence: float = Field(description="结论可信度 0~1")
    needs_review: bool = Field(default=False, description="是否需要人工复核")
