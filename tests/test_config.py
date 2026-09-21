"""配置校验：默认值合法、越界值 fail-fast、API key 缺失 fail-fast。"""
import pytest
from pydantic import ValidationError

from app.config import Settings, _validate_api_key, settings


def test_defaults_valid():
    assert settings.llm_model
    assert 0.0 <= settings.llm_temperature <= 2.0
    assert settings.llm_timeout > 0
    assert settings.llm_max_retries >= 0
    assert settings.max_retry >= 0


def test_temperature_out_of_range_rejected():
    with pytest.raises(ValidationError):
        Settings(llm_temperature=3.0)


def test_max_retry_negative_rejected():
    with pytest.raises(ValidationError):
        Settings(max_retry=-1)


def test_api_key_fail_fast():
    with pytest.raises(RuntimeError):
        _validate_api_key("")
    with pytest.raises(RuntimeError):
        _validate_api_key("sk-placeholder")
    assert _validate_api_key("sk-real-key") == "sk-real-key"
