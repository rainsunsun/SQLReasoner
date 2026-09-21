"""CLI 入口：问一个数据分析问题，跑完整的多 agent SOP 流水线。

用法：
    python main.py "2026-09-01 这两个小时 GitHub 上哪种事件最多？"
"""
from __future__ import annotations

import logging
import sys

from langgraph.types import Command

from app.graph.workflow import build_graph
from app.log import configure_logging

logger = logging.getLogger(__name__)

DEFAULT_QUESTION = "2026-09-01 00:00 到 02:00 这两个小时，GitHub 上哪种事件类型最多？"


def run(question: str) -> None:
    graph = build_graph()
    config = {"configurable": {"thread_id": "main"}}

    result = graph.invoke({"question": question}, config)

    # 可能有多轮人工复核：拒绝会回到 plan 重新分析，可能再次触发复核，故用 while 循环
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print("\n[人工复核] 需要人工复核：")
        print("  提示:", payload["question"])
        print("  结论:", payload["answer"])
        print("  置信度:", payload["confidence"])
        for f in payload["key_findings"]:
            print("    -", f)
        decision = input("\n输入决定（accept 接受 / reject 重新分析）: ").strip() or "accept"
        result = graph.invoke(Command(resume=decision), config)

    rep = result["report"]
    print("\n" + "=" * 50)
    print("[分析报告]")
    print("=" * 50)
    print("回答:", rep.answer)
    print("\n关键发现:")
    for f in rep.key_findings:
        print("  -", f)
    print("\n数据依据:", rep.evidence)
    print("可信度:", rep.confidence)


def main() -> int:
    # Windows 控制台默认 GBK，强制 UTF-8 避免中文/特殊符号打印报错
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    configure_logging()
    q = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUESTION
    try:
        run(q)
    except KeyboardInterrupt:
        print("\n已中断")
        return 130
    except Exception as e:  # noqa: BLE001
        logger.exception("流水线执行失败")
        print(f"\n[错误] 执行失败：{e}\n（详见日志）")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
