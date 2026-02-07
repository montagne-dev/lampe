"""Unit tests for LLM aggregation workflow with mute_issue tool."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lampe.review.workflows.pr_review.data_models import (
    AgentReviewOutput,
    FileReview,
    ReviewComment,
)
from lampe.review.workflows.pr_review.llm_aggregation_step import (
    LLMAggregationCompleteEvent,
    LLMAggregationStartEvent,
    LLMAggregationWorkflow,
    _apply_muted_flags,
    _build_issues_with_ids,
)


@pytest.fixture
def sample_agent_reviews():
    """Create sample agent reviews for testing."""
    return [
        AgentReviewOutput(
            agent_name='SecurityAgent',
            focus_areas=['security'],
            reviews=[
                FileReview(
                    file_path='src/auth.py',
                    line_comments={'15': 'Consider adding null check'},
                    structured_comments=[
                        ReviewComment(
                            line_number=42,
                            comment='Missing input validation',
                            severity='high',
                            category='security',
                            agent_name='SecurityAgent',
                        ),
                        ReviewComment(
                            line_number=50,
                            comment='Looks good',
                            severity='low',
                            category='quality',
                            agent_name='SecurityAgent',
                        ),
                    ],
                    summary='Review summary',
                    agent_name='SecurityAgent',
                ),
            ],
            sources=[],
            summary='Security review done',
        ),
    ]


def test_build_issues_with_ids(sample_agent_reviews):
    """Test that issue IDs are built correctly."""
    issues_json = _build_issues_with_ids(sample_agent_reviews)
    assert '0|0|s|0' in issues_json
    assert '0|0|s|1' in issues_json
    assert '0|0|l|15' in issues_json
    assert 'Missing input validation' in issues_json
    assert 'Looks good' in issues_json


def test_apply_muted_flags(sample_agent_reviews):
    """Test that muted flags are applied correctly based on issue IDs."""
    muted_ids = {'0|0|s|1', '0|0|l|15'}  # Mute second structured comment and line comment

    result = _apply_muted_flags(sample_agent_reviews, muted_ids)

    assert len(result) == 1
    file_review = result[0].reviews[0]
    # First structured comment: not muted
    assert file_review.structured_comments[0].muted is False
    # Second structured comment: muted
    assert file_review.structured_comments[1].muted is True
    # Line comment 15: muted
    assert '15' in file_review.muted_line_numbers


@pytest.mark.asyncio
async def test_llm_aggregation_with_tool_calls(sample_agent_reviews):
    """Test that LLM aggregation workflow applies muted flags from tool calls."""
    # Create mock tool call - LLM mutes issue 0|0|s|1 (the "Looks good" comment)
    mock_tool_call = MagicMock()
    mock_tool_call.tool_name = 'mute_issue'
    mock_tool_call.tool_id = 'call_123'
    mock_tool_call.tool_kwargs = {'issue_id': '0|0|s|1'}

    # First response: has tool calls
    mock_response_with_tools = MagicMock()
    mock_response_with_tools.message.content = None
    mock_response_with_tools.message.additional_kwargs = {}

    # Second response: no tool calls (done)
    mock_response_done = MagicMock()
    mock_response_done.message.content = 'Muted 1 issue: non-actionable comment'
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

    workflow = LLMAggregationWorkflow(verbose=False, llm=mock_llm)
    result = await workflow.run(
        start_event=LLMAggregationStartEvent(
            agent_reviews=sample_agent_reviews,
            files_changed='src/auth.py | +10 -5',
        )
    )

    assert isinstance(result, LLMAggregationCompleteEvent)
    assert len(result.aggregated_reviews) == 1
    # The "Looks good" comment (index 1) should be muted
    assert result.aggregated_reviews[0].reviews[0].structured_comments[1].muted is True
    assert result.aggregated_reviews[0].reviews[0].structured_comments[0].muted is False


@pytest.mark.asyncio
async def test_llm_aggregation_empty_reviews():
    """Test that empty reviews return empty result."""
    workflow = LLMAggregationWorkflow(verbose=False)
    result = await workflow.run(
        start_event=LLMAggregationStartEvent(agent_reviews=[], files_changed='')
    )
    assert isinstance(result, LLMAggregationCompleteEvent)
    assert result.aggregated_reviews == []


@pytest.mark.asyncio
async def test_llm_aggregation_fallback_on_error(sample_agent_reviews):
    """Test that workflow falls back to original reviews on LLM error."""
    mock_llm = MagicMock()
    mock_llm.achat_with_tools = AsyncMock(side_effect=Exception('LLM error'))
    mock_llm.get_tool_calls_from_response = MagicMock(return_value=[])

    workflow = LLMAggregationWorkflow(verbose=False, llm=mock_llm)
    result = await workflow.run(
        start_event=LLMAggregationStartEvent(
            agent_reviews=sample_agent_reviews,
            files_changed='src/auth.py | +10 -5',
        )
    )

    assert isinstance(result, LLMAggregationCompleteEvent)
    assert len(result.aggregated_reviews) == 1
    # Original reviews returned (no muted flags applied)
    assert result.aggregated_reviews[0].reviews[0].structured_comments[0].muted is False
