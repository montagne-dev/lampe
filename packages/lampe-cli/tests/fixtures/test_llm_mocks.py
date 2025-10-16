"""
Test fixtures for LLM mocking in lampe-cli tests.
"""

from unittest.mock import MagicMock


def create_mock_llm_response(content: str):
    """Create a mock LLM response with the given content."""
    mock_response = MagicMock()
    mock_response.message.content = content
    return mock_response


def create_mock_llm_response_with_markdown(content: str):
    """Create a mock LLM response wrapped in markdown code blocks."""
    wrapped_content = f"```md\n{content}\n```"
    return create_mock_llm_response(wrapped_content)


def create_mock_llm_error(error_message: str):
    """Create a mock LLM that raises an error."""

    def mock_achat(*args, **kwargs):
        raise Exception(error_message)

    mock_llm = MagicMock()
    mock_llm.achat = mock_achat
    return mock_llm


def create_mock_llm_with_tool_calls(tool_calls: list):
    """Create a mock LLM response with tool calls."""
    mock_response = MagicMock()
    mock_response.message.content = None
    mock_response.message.tool_calls = tool_calls
    return mock_response


# Predefined mock responses for common test scenarios
MOCK_RESPONSES = {
    "simple_description": create_mock_llm_response(
        "### What change is being made?\n\nAdded a new feature.\n\n### Why are these changes being made?\n\nTo improve the product."  # noqa: E501
    ),
    "detailed_description": create_mock_llm_response(
        "### What change is being made?\n\nImplemented a comprehensive authentication system including:\n- JWT token generation and validation\n- Secure token storage and management\n- User session handling\n\n### Why are these changes being made?\n\nTo enhance application security and provide a scalable authentication solution."  # noqa: E501
    ),
    "markdown_wrapped": create_mock_llm_response_with_markdown(
        "### What change is being made?\n\nAdded authentication system.\n\n### Why are these changes being made?\n\nTo improve security."  # noqa: E501
    ),
    "empty_response": create_mock_llm_response(""),
    "error_response": create_mock_llm_error("LLM service unavailable"),
    "timeout_response": create_mock_llm_error("Request timeout"),
    "invalid_json_response": create_mock_llm_response("This is not a valid JSON response for the expected format."),
}


def get_mock_response(scenario: str):
    """Get a predefined mock response for a test scenario."""
    return MOCK_RESPONSES.get(scenario, MOCK_RESPONSES["simple_description"])


def create_mock_workflow_result(description: str):
    """Create a mock workflow result with the given description."""
    mock_result = MagicMock()
    mock_result.description = description
    return mock_result


def create_mock_generator_adapter(description: str):
    """Create a mock generator adapter that returns the given description."""
    mock_adapter = MagicMock()
    mock_adapter.generate = MagicMock(return_value=create_mock_workflow_result(description))
    return mock_adapter


def create_mock_provider():
    """Create a mock provider for testing."""
    mock_provider = MagicMock()
    mock_provider.deliver_pr_description = MagicMock()
    return mock_provider
