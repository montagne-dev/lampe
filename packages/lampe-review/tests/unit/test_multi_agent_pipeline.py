"""Unit tests for multi-agent pipeline."""

from unittest.mock import AsyncMock

import pytest

from lampe.review.workflows.pr_review.data_models import (
    AgentReviewOutput,
    FileReview,
    PRReviewInput,
    PullRequest,
    Repository,
    ReviewDepth,
)
from lampe.review.workflows.pr_review.multi_agent_pipeline import (
    MultiAgentPipelineWorkflow,
    generate_multi_agent_pr_review,
)


@pytest.fixture
def mock_repository():
    """Create a mock repository for testing."""
    return Repository(full_name="test/repo", local_path="/tmp/test-repo")


@pytest.fixture
def mock_pull_request():
    """Create a mock pull request for testing."""
    return PullRequest(
        number=123,
        title="Test PR",
        body="This is a test PR",
        base_commit_hash="abc123",
        base_branch_name="main",
        head_commit_hash="def456",
        head_branch_name="feature/test",
    )


@pytest.fixture
def mock_agent_output():
    """Create a mock agent output for testing."""
    return AgentReviewOutput(
        agent_name="Test Agent",
        focus_areas=["test"],
        reviews=[
            FileReview(
                file_path="test.py", line_comments={1: "Test comment"}, summary="Test summary", agent_name="Test Agent"
            )
        ],
        summary="Test agent summary",
    )


@pytest.mark.asyncio
async def test_multi_agent_pipeline_initialization():
    """Test that the pipeline initializes correctly."""
    pipeline = MultiAgentPipelineWorkflow(timeout=30, verbose=True)

    assert pipeline.timeout == 30
    assert pipeline.verbose is True
    assert len(pipeline.agents) == 6  # Should have 6 specialized agents
    assert pipeline.aggregator is not None


@pytest.mark.asyncio
async def test_multi_agent_pipeline_execution(mock_repository, mock_pull_request, mock_agent_output):
    """Test that the pipeline executes all agents and aggregates results."""
    # Mock the agents to return predictable output
    pipeline = MultiAgentPipelineWorkflow(verbose=True)

    # Mock all agents to return the same output
    for agent in pipeline.agents:
        agent.review = AsyncMock(return_value=mock_agent_output)

    # Create input
    input_data = PRReviewInput(
        repository=mock_repository,
        pull_request=mock_pull_request,
        review_depth=ReviewDepth.STANDARD,
        use_multi_agent=True,
    )

    # Execute pipeline using the workflow
    result = await generate_multi_agent_pr_review(
        repository=mock_repository,
        pull_request=mock_pull_request,
        review_depth=ReviewDepth.STANDARD,
        verbose=True,
    )

    # Verify results
    assert result is not None
    assert hasattr(result, "reviews")
    assert len(result.reviews) > 0  # Should have aggregated reviews


@pytest.mark.asyncio
async def test_agent_failure_handling(mock_repository, mock_pull_request):
    """Test that pipeline continues when individual agents fail."""
    pipeline = MultiAgentPipelineWorkflow(verbose=True)

    # Mock first agent to fail, others to succeed
    pipeline.agents[0].review = AsyncMock(side_effect=Exception("Agent failed"))
    for agent in pipeline.agents[1:]:
        agent.review = AsyncMock(
            return_value=AgentReviewOutput(
                agent_name="Working Agent", focus_areas=["test"], reviews=[], summary="Success"
            )
        )

    # Should not raise exception even if some agents fail
    result = await generate_multi_agent_pr_review(
        repository=mock_repository,
        pull_request=mock_pull_request,
        review_depth=ReviewDepth.STANDARD,
        verbose=True,
    )
    assert result is not None
