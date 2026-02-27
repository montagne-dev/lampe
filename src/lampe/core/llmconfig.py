import os
from enum import StrEnum


class MODELS(StrEnum):
    CLAUDE_3_5_SONNET_2024_10_22 = "anthropic/claude-3-5-sonnet-20241022"
    CLAUDE_4_5_SONNET_2025_09_29 = "anthropic/claude-sonnet-4-5-20250929"
    GPT_5_NANO_2025_08_07 = "openai/gpt-5-nano-2025-08-07"
    GPT_5_MINI_2025_08_07 = "openai/gpt-5-mini-2025-08-07"
    GPT_5_2025_08_07 = "openai/gpt-5-2025-08-07"
    GPT_5_1_2025_11_13 = "openai/gpt-5.1-2025-11-13"
    GPT_5_2_2025_12_11 = "openai/gpt-5.2-2025-12-11"
    GPT_5_2_CODEX = "openai/gpt-5.2-codex"
    GPT_5_1_CODEX_MINI = "openai/gpt-5.1-codex-mini"
    GPT_4_0613 = "openai/gpt-4-0613"


def get_model(env_var: str, default: str) -> str:
    """Return model from env var or default. For use with LAMPE_MODEL_* variables."""
    return os.getenv(env_var) or default


def provider_from_model(model: str) -> str | None:
    """Extract provider from LiteLLM model string (e.g. anthropic/claude-..., openai/gpt-...)."""
    m = model.lower()
    if "anthropic" in m:
        return "anthropic"
    if "openai" in m:
        return "openai"
    return None
