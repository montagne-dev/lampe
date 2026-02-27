"""Tests for lampe.core.llmconfig."""

import pytest

from lampe.core.llmconfig import MODELS, get_model, provider_from_model


def test_get_model_returns_env_value_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAMPE_MODEL_DESCRIBE", "anthropic/claude-3-5-sonnet")
    assert get_model("LAMPE_MODEL_DESCRIBE", str(MODELS.GPT_5_NANO_2025_08_07)) == ("anthropic/claude-3-5-sonnet")


def test_get_model_returns_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LAMPE_MODEL_DESCRIBE", raising=False)
    assert get_model("LAMPE_MODEL_DESCRIBE", str(MODELS.GPT_5_NANO_2025_08_07)) == ("openai/gpt-5-nano-2025-08-07")


def test_get_model_returns_default_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAMPE_MODEL_DESCRIBE", "")
    assert get_model("LAMPE_MODEL_DESCRIBE", str(MODELS.GPT_5_NANO_2025_08_07)) == ("openai/gpt-5-nano-2025-08-07")


def test_provider_from_model_anthropic() -> None:
    assert provider_from_model("anthropic/claude-3-5-sonnet-20241022") == "anthropic"
    assert provider_from_model("ANTHROPIC/CLAUDE-3") == "anthropic"


def test_provider_from_model_openai() -> None:
    assert provider_from_model("openai/gpt-5-2025-08-07") == "openai"
    assert provider_from_model("OPENAI/GPT-5") == "openai"


def test_provider_from_model_unknown() -> None:
    assert provider_from_model("custom/my-model") is None
    assert provider_from_model("unknown-provider") is None
