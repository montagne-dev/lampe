"""Utilities for parsing LLM JSON responses with graceful handling of malformed output."""

import re

from llama_index.core.output_parsers import PydanticOutputParser

from lampe.review.workflows.agentic_review.data_models import ValidationAgentResponseModel


def extract_json_from_llm_content(content: str) -> str:
    """Extract JSON from LLM response, supporting markdown code blocks."""
    if not content or not content.strip():
        return ""
    stripped = content.strip()

    # Try markdown code block with json language tag
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try generic code block
    match = re.search(r"```\s*\n(.*?)\n```", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()

    return stripped


def parse_validation_response(content: str) -> tuple[ValidationAgentResponseModel | None, bool]:
    """
    Parse LLM content into ValidationAgentResponseModel.

    Returns (parsed_model, success). On failure returns (None, False).
    """
    extracted = extract_json_from_llm_content(content)
    if not extracted:
        return None, False

    # Workaround: some models insert newlines before closing quotes
    normalized = extracted.replace('\n"', '"')

    try:
        parser = PydanticOutputParser(output_cls=ValidationAgentResponseModel)
        parsed = parser.parse(normalized)
        return parsed, True
    except Exception:
        return None, False
