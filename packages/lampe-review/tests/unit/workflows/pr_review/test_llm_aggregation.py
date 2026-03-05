"""Unit tests for LLM aggregation workflow with mute_issue tool."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from llama_index.core.tools import ToolSelection

from lampe.core.workflows.function_calling_agent import ToolSource
from lampe.review.workflows.pr_review.data_models import (
    AgentReviewOutput,
    FileReview,
    IssueWithId,
    ReviewComment,
)
from lampe.review.workflows.pr_review.llm_aggregation_step import (
    LLMAggregationCompleteEvent,
    LLMAggregationStartEvent,
    LLMAggregationWorkflow,
    _apply_muted_flags,
    _build_issues_with_ids,
    _format_sources_for_display,
)


@pytest.fixture
def sample_agent_reviews():
    """Create sample agent reviews for testing."""
    return [
        AgentReviewOutput(
            agent_name="SecurityAgent",
            focus_areas=["security"],
            reviews=[
                FileReview(
                    file_path="src/auth.py",
                    line_comments={"15": "Consider adding null check"},
                    structured_comments=[
                        ReviewComment(
                            line_number=42,
                            comment="Missing input validation",
                            severity="high",
                            category="security",
                            agent_name="SecurityAgent",
                        ),
                        ReviewComment(
                            line_number=50,
                            comment="Looks good",
                            severity="low",
                            category="quality",
                            agent_name="SecurityAgent",
                        ),
                    ],
                    summary="Review summary",
                    agent_name="SecurityAgent",
                ),
            ],
            sources=[],
            summary="Security review done",
        ),
    ]


def test_build_issues_with_ids(sample_agent_reviews):
    """Test that issue IDs are built correctly via IssueWithId model."""
    issues_json = _build_issues_with_ids(sample_agent_reviews)
    assert "0|0|s|0" in issues_json
    assert "0|0|s|1" in issues_json
    assert "0|0|l|15" in issues_json
    assert "Missing input validation" in issues_json
    assert "Looks good" in issues_json


def test_issue_with_id_build_and_format(sample_agent_reviews):
    """Test IssueWithId model: build_from_agent_reviews and format_list_for_prompt."""
    issues = IssueWithId.build_from_agent_reviews(sample_agent_reviews)
    assert len(issues) == 3
    assert issues[0].issue_id == "0|0|s|0"
    assert issues[0].comment == "Missing input validation"
    assert issues[2].issue_id == "0|0|l|15"

    formatted = IssueWithId.format_list_for_prompt(issues)
    assert "### Issue `0|0|s|0`" in formatted
    assert "**Agent:** SecurityAgent" in formatted
    assert "_No issues to review._" == IssueWithId.format_list_for_prompt([])


def test_format_sources_for_display_includes_tool_name_and_kwargs_only():
    """Tools used section shows tool_name + kwargs, not output."""
    reviews = [
        AgentReviewOutput(
            agent_name="QuickReview",
            focus_areas=["security"],
            reviews=[],
            sources=[
                ToolSource(
                    tool_name="get_file_content_at_commit",
                    tool_kwargs={"path": "src/auth.py", "line_start": 1, "line_end": 50},
                    tool_output="<omitted>",
                ),
                ToolSource(
                    tool_name="search_in_files",
                    tool_kwargs={"pattern": "authenticate", "relative_dir_path": "src"},
                    tool_output="<omitted>",
                ),
            ],
            summary="",
        ),
    ]
    result = _format_sources_for_display(reviews)
    assert "get_file_content_at_commit" in result
    assert "search_in_files" in result
    assert "src/auth.py" in result
    assert "authenticate" in result
    assert "<omitted>" not in result


def test_format_sources_for_display_empty_when_no_sources():
    """When all agents have empty sources, return empty string."""
    reviews = [
        AgentReviewOutput(agent_name="A", focus_areas=[], reviews=[], sources=[], summary=""),
    ]
    assert _format_sources_for_display(reviews) == ""


def test_apply_muted_flags(sample_agent_reviews):
    """Test that muted flags and reasons are applied correctly based on issue IDs."""
    muted_reasons = {
        "0|0|s|1": "non-actionable",
        "0|0|l|15": "noisy",
    }

    result = _apply_muted_flags(sample_agent_reviews, muted_reasons)

    assert len(result) == 1
    file_review = result[0].reviews[0]
    # First structured comment: not muted
    assert file_review.structured_comments[0].muted is False
    assert file_review.structured_comments[0].mute_reason is None
    # Second structured comment: muted with reason
    assert file_review.structured_comments[1].muted is True
    assert file_review.structured_comments[1].mute_reason == "non-actionable"
    # Line comment 15: muted with reason
    assert "15" in file_review.muted_line_numbers
    assert file_review.muted_line_reasons.get("15") == "noisy"


@pytest.mark.asyncio
async def test_llm_aggregation_with_tool_calls(sample_agent_reviews):
    """Test that LLM aggregation workflow applies muted flags from tool calls."""
    # Create tool call - LLM mutes issue 0|0|s|1 (the "Looks good" comment) with reason
    mock_tool_call = ToolSelection(
        tool_id="call_123",
        tool_name="mute_issue",
        tool_kwargs={"issue_id": "0|0|s|1", "reason": "non-actionable"},
    )

    # First response: has tool calls
    mock_response_with_tools = MagicMock()
    mock_response_with_tools.message.content = None
    mock_response_with_tools.message.additional_kwargs = {}

    # Second response: no tool calls (done)
    mock_response_done = MagicMock()
    mock_response_done.message.content = "Muted 1 issue: non-actionable comment"
    mock_response_done.message.additional_kwargs = {}

    call_count = 0

    async def mock_achat_with_tools(tools, chat_history):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_response_with_tools
        return mock_response_done

    def mock_get_tool_calls(response, error_on_no_tool_call=False):
        nonlocal call_count
        if call_count == 1 and response is mock_response_with_tools:
            return [mock_tool_call]
        return []

    mock_llm = MagicMock()
    mock_llm.achat_with_tools = AsyncMock(side_effect=mock_achat_with_tools)
    mock_llm.get_tool_calls_from_response = mock_get_tool_calls
    mock_llm.metadata.is_function_calling_model = True

    workflow = LLMAggregationWorkflow(verbose=False, llm=mock_llm)
    result = await workflow.run(
        start_event=LLMAggregationStartEvent(
            agent_reviews=sample_agent_reviews,
            files_changed="src/auth.py | +10 -5",
        )
    )

    assert isinstance(result, LLMAggregationCompleteEvent)
    assert len(result.aggregated_reviews) == 1
    # The "Looks good" comment (index 1) should be muted with reason
    assert result.aggregated_reviews[0].reviews[0].structured_comments[1].muted is True
    assert result.aggregated_reviews[0].reviews[0].structured_comments[1].mute_reason == "non-actionable"
    assert result.aggregated_reviews[0].reviews[0].structured_comments[0].muted is False


@pytest.mark.asyncio
async def test_llm_aggregation_empty_reviews():
    """Test that empty reviews return empty result."""
    workflow = LLMAggregationWorkflow(verbose=False)
    result = await workflow.run(start_event=LLMAggregationStartEvent(agent_reviews=[], files_changed=""))
    assert isinstance(result, LLMAggregationCompleteEvent)
    assert result.aggregated_reviews == []


@pytest.mark.asyncio
async def test_llm_aggregation_fallback_on_error(sample_agent_reviews):
    """Test that workflow falls back to original reviews on LLM error."""
    mock_llm = MagicMock()
    mock_llm.achat_with_tools = AsyncMock(side_effect=Exception("LLM error"))
    mock_llm.get_tool_calls_from_response = MagicMock(return_value=[])
    mock_llm.metadata.is_function_calling_model = True

    workflow = LLMAggregationWorkflow(verbose=False, llm=mock_llm)
    result = await workflow.run(
        start_event=LLMAggregationStartEvent(
            agent_reviews=sample_agent_reviews,
            files_changed="src/auth.py | +10 -5",
        )
    )

    assert isinstance(result, LLMAggregationCompleteEvent)
    assert len(result.aggregated_reviews) == 1
    # Original reviews returned (no muted flags applied)
    assert result.aggregated_reviews[0].reviews[0].structured_comments[0].muted is False
