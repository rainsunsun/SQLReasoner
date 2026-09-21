"""可插拔 LLM：默认 DeepSeek（OpenAI 兼容），可切 Claude/Qwen/GLM。"""
from __future__ import annotations

from langchain_openai import ChatOpenAI

from app import config


def get_llm(temperature: float | None = None, model: str | None = None) -> ChatOpenAI:
    return ChatOpenAI(
        model=model or config.LLM_MODEL,
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY or "sk-placeholder",
        temperature=config.LLM_TEMPERATURE if temperature is None else temperature,
    )
