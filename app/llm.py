"""可插拔 LLM：默认 DeepSeek（OpenAI 兼容），可切 Claude/Qwen/GLM。

稳健性：
- request_timeout：单次请求超时，防止 LLM 挂起拖死流水线
- max_retries：瞬时错误（网络抖动/限流）自动重试
- invoke_structured：结构化输出统一入口，解析/网络失败自动重试
"""
from __future__ import annotations

import logging
from typing import TypeVar

from langchain_openai import ChatOpenAI

from app.config import require_api_key, settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


def get_llm(temperature: float | None = None, model: str | None = None) -> ChatOpenAI:
    """构造 LLM 客户端（带超时 + 重试）。没有真实 key 直接 fail fast。"""
    require_api_key()
    return ChatOpenAI(
        model=model or settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        temperature=settings.llm_temperature if temperature is None else temperature,
        request_timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )


def invoke_structured(
    schema: type[T],
    system: str,
    human: str,
    *,
    temperature: float | None = None,
    retries: int | None = None,
) -> T:
    """以结构化输出调用 LLM；失败自动重试，最后一次失败才抛出。

    覆盖两类失败：瞬时网络错误、结构化输出解析失败（LLM 返回内容不符合 schema）。
    """
    llm = get_llm(temperature=temperature).with_structured_output(schema, method="function_calling")
    attempts = (settings.llm_max_retries if retries is None else retries) + 1
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return llm.invoke([("system", system), ("human", human)])
        except Exception as e:  # noqa: BLE001
            last = e
            logger.warning("结构化输出失败（%d/%d）：%s", attempt + 1, attempts, e)
    assert last is not None  # attempts >= 1，循环至少执行一次
    raise last
