"""全局配置：pydantic-settings 校验，缺 key / 非法值 fail-fast。

- LLM / 运行参数从 .env 读取，加载时做类型与范围校验（温度越界、重试为负等直接报错）
- API key 在真正调用 LLM 时 fail-fast（缺失或仍为占位符直接抛错，避免带假 key 跑出诡异结果）
- 路径常量（DATA_DIR / DB_PATH）是派生值，不是用户设置
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "analytics.duckdb"
CHECKPOINT_PATH = DATA_DIR / "checkpoints.sqlite"  # HITL 会话状态落盘

# 先加载 .env 到环境变量（文件不存在时静默跳过），Settings 再统一读取
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    """运行配置。字段名与 .env 里的大写环境变量一一对应（大小写不敏感）。"""

    model_config = SettingsConfigDict(extra="ignore")

    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_timeout: float = Field(default=60.0, gt=0)  # 单次 LLM 请求超时（秒）
    llm_max_retries: int = Field(default=2, ge=0)   # 瞬时错误（网络/限流）重试次数

    max_retry: int = Field(default=3, ge=0)  # SQL 执行失败时的自我修复最大重试次数


settings = Settings()

_PLACEHOLDER_KEYS = {"", "sk-placeholder", "sk-xxx", "your-api-key", "changeme"}


def _validate_api_key(key: str) -> str:
    """校验 API key：缺失或占位符直接抛错（fail fast）。"""
    key = (key or "").strip()
    if key.lower() in _PLACEHOLDER_KEYS:
        raise RuntimeError(
            "LLM_API_KEY 未配置或仍为占位符：请在 .env 填入真实 key"
            "（可复制 .env.example 改名 .env）"
        )
    return key


def require_api_key() -> str:
    """取真实 API key，缺失时 fail fast。"""
    return _validate_api_key(settings.llm_api_key)
