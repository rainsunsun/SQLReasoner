"""统一日志：输出到 stderr，不污染 stdout 的主流程打印。"""
from __future__ import annotations

import logging
import sys

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_DATE_FORMAT = "%H:%M:%S"


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if not root.handlers:  # 幂等：避免重复添加 handler
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
        root.addHandler(handler)
    root.setLevel(level)
