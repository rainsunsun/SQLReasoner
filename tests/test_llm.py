"""LLM 客户端：缺 key fail-fast、有 key 能构造（不发起网络请求）。"""
import pytest

from app import config
from app.llm import get_llm


def test_get_llm_requires_key(monkeypatch):
    monkeypatch.setattr(config.settings, "llm_api_key", "")
    with pytest.raises(RuntimeError):
        get_llm()


def test_get_llm_constructs(monkeypatch):
    monkeypatch.setattr(config.settings, "llm_api_key", "sk-test")
    assert get_llm() is not None
