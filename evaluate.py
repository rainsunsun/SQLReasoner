"""评估：多 agent 数据分析流水线 vs 单 LLM 基线。

三组对照，回答两个核心问题：
1. 多 agent（拆 5 个 + self-repair + 校验）比「单 LLM 一次写 SQL」好在哪？
2. self-repair 到底修复了多少执行失败？

配置：
- single-shot：单 LLM 一次直接输出 {sql, answer}，SQL 执行一次（无修复、无校验、无多 agent）
- multi-agent：完整 LangGraph 流水线（需求分析→规划→执行[含 self-repair]→校验→报告，含 HITL）
- no-repair  ：多 agent 的前两步（understand+plan）出的原始 SQL 直接执行，不修复
                 —— 与 multi-agent 唯一差别是「修不修复」，用来隔离 self-repair 的贡献

用法：
    python evaluate.py             # 跑全部 12 问
    python evaluate.py --limit 4   # 只跑前 4 问（快速冒烟）
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from langgraph.types import Command
from pydantic import BaseModel, Field

from app.agents import linker, planner, understand
from app.graph.workflow import build_graph
from app.llm import get_llm
from app.tools.db import execute_sql
from app.tools.schema import get_schema_text
from data.eval.questions import QUESTIONS

# Windows 终端默认 GBK，强制 UTF-8 避免中文/符号打印报错（必须在任何 print 之前）
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------- 判题：确定性、可复现（不引入 LLM 判题 bias） ----------

def _normalize(s: str) -> str:
    """去大小写、空格、逗号、标点，只留字母数字，用于模糊精确匹配。"""
    return "".join(ch for ch in s.lower() if ch.isalnum())


def judge(answer: str, keys: list[str]) -> bool:
    """答案必须包含所有关键事实（实体 + 精确数字）才算对。"""
    a = _normalize(answer)
    return all(_normalize(k) in a for k in keys)


# ---------- 配置 A：单 LLM 一次写 SQL + 出结论 ----------

class _OneShot(BaseModel):
    sql: str = Field(description="回答该问题的一条只读 SELECT")
    answer: str = Field(description="一句话结论，必须包含具体数字")


_ONE_SHOT_SYSTEM = """你是数据分析专家。下面有一个关于 GitHub 事件表的问题，请直接写一条 SQL 并给出结论。

数据表 events 结构：
- id VARCHAR, type VARCHAR, actor_login VARCHAR, repo_name VARCHAR
- created_at TIMESTAMP（时间过滤直接用 created_at >= '2026-09-01 00:00:00'）
- action VARCHAR, payload VARCHAR（JSON 字符串，用 json_extract_string 解析）

要求：
1. sql：一条只读 SELECT，直接回答这个问题
2. answer：一句话给出结论，必须包含具体数字
"""


def single_shot(question: str) -> dict:
    llm = get_llm().with_structured_output(_OneShot, method="function_calling")
    out = llm.invoke([("system", _ONE_SHOT_SYSTEM), ("human", f"问题：{question}")])
    res = execute_sql(out.sql)
    return {"success": res.success, "answer": out.answer, "sql": out.sql}


# ---------- 配置 B：完整多 agent 流水线 ----------

def multi_agent(question: str, idx: int) -> dict:
    graph = build_graph()
    config = {"configurable": {"thread_id": f"eval-{idx}"}}
    result = graph.invoke({"question": question}, config)
    # 评估时若触发人工复核，自动接受（衡量的是系统自动产出质量，人工兜底是另一层）
    while "__interrupt__" in result:
        result = graph.invoke(Command(resume="accept"), config)

    results = result.get("results", [])
    success = all(r.success for r in results)
    return {"success": success, "answer": result["report"].answer, "results": results}


# ---------- 配置 C：多 agent 原始 SQL 但无 self-repair ----------

def no_repair(question: str) -> bool:
    """只走 understand + link + plan 出 SQL，直接执行一次，失败就算失败（不修复）。"""
    goal = understand.understand(question)
    linked = linker.link(question, goal, get_schema_text())
    plan = planner.plan(goal, linked)
    if not plan.steps:
        return False
    return all(execute_sql(step.sql).success for step in plan.steps)


# ---------- 主流程 ----------

def run(limit: int) -> None:
    rows = []
    for i, item in enumerate(QUESTIONS[:limit]):
        qid, question, keys = item["id"], item["question"], item["keys"]

        a = single_shot(question)
        b = multi_agent(question, i)
        c_ok = no_repair(question)

        a_missing = [k for k in keys if _normalize(k) not in _normalize(a["answer"])]
        b_missing = [k for k in keys if _normalize(k) not in _normalize(b["answer"])]
        rows.append(
            {
                "id": qid,
                "question": question,
                "a_exec": a["success"],
                "a_ok": not a_missing,
                "a_answer": a["answer"],
                "a_missing": a_missing,
                "b_exec": b["success"],
                "b_ok": not b_missing,
                "b_answer": b["answer"],
                "b_missing": b_missing,
                "c_exec": c_ok,
            }
        )
        print(f"[{qid}] single-shot exec={a['success']} ans={'✓' if judge(a['answer'], keys) else '✗'} | "
              f"multi-agent exec={b['success']} ans={'✓' if judge(b['answer'], keys) else '✗'} | "
              f"no-repair exec={c_ok}")

    # 汇总
    n = len(rows)
    a_exec = sum(r["a_exec"] for r in rows)
    a_ok = sum(r["a_ok"] for r in rows)
    a_end2end = sum(r["a_exec"] and r["a_ok"] for r in rows)
    b_exec = sum(r["b_exec"] for r in rows)
    b_ok = sum(r["b_ok"] for r in rows)
    b_end2end = sum(r["b_exec"] and r["b_ok"] for r in rows)
    c_exec = sum(r["c_exec"] for r in rows)

    report = _render_report(rows, a_exec, a_ok, a_end2end, b_exec, b_ok, b_end2end, c_exec, n)
    print("\n" + report)

    out = Path(__file__).resolve().parent / "data" / "eval" / "eval_report.md"
    out.write_text(report, encoding="utf-8")
    print(f"\n报告已写入 {out}")


def _render_report(rows, a_exec, a_ok, a_end2end, b_exec, b_ok, b_end2end, c_exec, n) -> str:
    def pct(x):
        return f"{x}/{n} = {x / n * 100:.0f}%"

    lines = []
    lines.append("# 数据分析多智能体 评估报告\n")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}　评估集规模：{n} 问（单表聚合类问题，答案预先算好）\n")
    lines.append("## 汇总指标\n")
    lines.append("| 指标 | single-shot（单 LLM） | multi-agent（多 agent+修复） | no-repair（多 agent 不修复） |")
    lines.append("|---|---|---|---|")
    lines.append(f"| SQL 执行成功率 | {pct(a_exec)} | {pct(b_exec)} | {pct(c_exec)} |")
    lines.append(f"| 答案正确率（含关键事实） | {pct(a_ok)} | {pct(b_ok)} | — |")
    lines.append(f"| 端到端正确率（查到且答对） | {pct(a_end2end)} | {pct(b_end2end)} | — |")
    lines.append("")
    lines.append(f"- self-repair 修复的执行失败：multi-agent {b_exec} 成功 vs no-repair {c_exec} 成功 → 修复了 **{b_exec - c_exec}** 个执行失败")
    lines.append(f"- 多 agent 相对单 LLM 的端到端提升：**{(b_end2end - a_end2end) / n * 100:.0f} 个百分点**\n")
    lines.append("## 逐题明细\n")
    lines.append("| # | 问题 | single-shot | multi-agent | no-repair |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        a = f"{'✓' if r['a_exec'] else '✗'}/{'✓' if r['a_ok'] else '✗'}"
        b = f"{'✓' if r['b_exec'] else '✗'}/{'✓' if r['b_ok'] else '✗'}"
        c = "✓" if r["c_exec"] else "✗"
        lines.append(f"| {r['id']} | {r['question']} | {a} | {b} | {c} |")
    lines.append("\n## 错题详情（缺失的关键事实）\n")
    has_error = False
    for r in rows:
        if r["a_missing"]:
            has_error = True
            lines.append(f"- **{r['id']}** single-shot 缺 `{', '.join(r['a_missing'])}`｜答案：{r['a_answer'][:80]}")
        if r["b_missing"]:
            has_error = True
            lines.append(f"- **{r['id']}** multi-agent 缺 `{', '.join(r['b_missing'])}`｜答案：{r['b_answer'][:80]}")
    if not has_error:
        lines.append("（无错题）")

    lines.append("\n> 说明：✓/✗ 前一个是「SQL 是否执行成功」，后一个是「答案是否含关键事实」。")
    lines.append("> 判题为确定性字符串匹配（归一化后），不引入 LLM 判题 bias；样本量小（12 问），结论方向性可信、绝对数值需谨慎。")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=len(QUESTIONS))
    args = ap.parse_args()
    run(args.limit)
