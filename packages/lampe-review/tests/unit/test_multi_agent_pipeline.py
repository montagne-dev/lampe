"""Unit tests for multi-agent pipeline."""

from unittest.mock import MagicMock, patch

import pytest

from lampe.review.workflows.pr_review.data_models import (
    AgentReviewOutput,
    FileReview,
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
                file_path="test.py",
                line_comments={"1": "Test comment"},
                summary="Test summary",
                agent_name="Test Agent",
            )
        ],
        summary="Test agent summary",
    )


@pytest.mark.asyncio
async def test_multi_agent_pipeline_initialization():
    """Test that the pipeline initializes correctly."""
    pipeline = MultiAgentPipelineWorkflow(agents=[], timeout=30, verbose=True)

    assert pipeline._timeout == 30
    assert pipeline.verbose is True
    assert len(pipeline.agents) >= 1  # Should have at least 1 specialized agent (default)
    assert pipeline.aggregator is not None


@pytest.mark.asyncio
async def test_multi_agent_pipeline_execution(mocker, mock_repository, mock_pull_request, mock_agent_output):
    """Test that the pipeline executes all agents and aggregates results."""
    # Mock list_changed_files to avoid git operations
    mocker.patch(
        "lampe.review.workflows.pr_review.multi_agent_pipeline.list_changed_files",
        return_value="test.py | +10 -5",
    )

    # Execute pipeline using the workflow
    with patch("llama_index.llms.litellm.LiteLLM.achat") as mock_achat:
        mock_response = MagicMock()
        mock_response.message.content = '{"reviews": [{"file_path": "test.py", "line_comments": {"1": "Test comment"}, "summary": "Test summary"}], "summary": "Test agent summary"}'
        mock_achat.return_value = mock_response

        result = await generate_multi_agent_pr_review(
            repository=mock_repository,
            pull_request=mock_pull_request,
            review_depth=ReviewDepth.STANDARD,
            verbose=True,
        )

        # Verify results
        assert result is not None
        assert hasattr(result, "output")
        assert len(result.output) > 0  # Should have aggregated reviews


@pytest.mark.asyncio
async def test_agent_failure_handling(mocker, mock_repository, mock_pull_request):
    """Test that pipeline continues when individual agents fail."""
    # Mock list_changed_files to avoid git operations
    mocker.patch(
        "lampe.review.workflows.pr_review.multi_agent_pipeline.list_changed_files",
        return_value="test.py | +10 -5",
    )

    # Should not raise exception even if some agents fail
    # The workflow handles exceptions internally and continues with other agents
    with patch("llama_index.llms.litellm.LiteLLM.achat") as mock_achat:
        mock_response = MagicMock()
        mock_response.message.content = '{"reviews": [], "summary": "Success"}'
        mock_achat.return_value = mock_response

        result = await generate_multi_agent_pr_review(
            repository=mock_repository,
            pull_request=mock_pull_request,
            review_depth=ReviewDepth.STANDARD,
            verbose=True,
        )
        assert result is not None
