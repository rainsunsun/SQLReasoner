"""全局配置：从 .env 读 LLM 与运行参数。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-placeholder")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))

DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "analytics.duckdb"

# 执行 agent 查询失败时的自我修复最大重试次数
MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))
