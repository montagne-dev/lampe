import tempfile
from unittest.mock import MagicMock, patch

import pytest

from lampe.cli.orchestrators.pr_review import PRReviewStart
from lampe.core.data_models import PullRequest, Repository
from lampe.review.workflows.pr_review.data_models import PRReviewInput, ReviewDepth
from lampe.review.workflows.pr_review.multi_agent_pipeline import (
    MultiAgentPipelineWorkflow,
    generate_multi_agent_pr_review,
)


@pytest.fixture
def mock_llm_response():
    mock = MagicMock()
    mock.message.content = """{
  "reviews": [
    {
      "file_path": "src/example.py",
      "line_comments": {
        "15": "Consider adding null check here",
        "42": "This could cause performance issues with large datasets"
      },
      "summary": "Overall good implementation, minor improvements suggested"
    }
  ]
}"""
    return mock


@pytest.fixture
def sample_repository():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Repository(local_path=temp_dir)


@pytest.fixture
def sample_pull_request():
    return PullRequest(
        number=1,
        title="Add new feature",
        body="This PR adds a new feature.",
        base_commit_hash="abc123",
        base_branch_name="main",
        head_commit_hash="def456",
        head_branch_name="feature/new-feature",
    )


@pytest.mark.asyncio
async def test_pr_review_workflow_run(mocker, mock_llm_response, sample_repository, sample_pull_request):
    mocker.patch(
        "lampe.review.workflows.pr_review.multi_agent_pipeline.list_changed_files",
        return_value="src/example.py | +10 -5",
    )

    workflow = MultiAgentPipelineWorkflow(agents=[], timeout=None, verbose=False)

    with patch("llama_index.llms.litellm.LiteLLM.achat", return_value=mock_llm_response) as mock_achat:
        result = await workflow.run(
            start_event=PRReviewStart(
                input=PRReviewInput(
                    repository=sample_repository,
                    pull_request=sample_pull_request,
                    review_depth=ReviewDepth.STANDARD,
                    custom_guidelines=None,
                    files_exclude_patterns=None,
                )
            )
        )
        assert result.reviews[0]["file_path"] == "src/example.py"
        assert result.reviews[0]["line_comments"]["15"] == "Consider adding null check here"
        assert result.reviews[0]["summary"] == "Overall good implementation, minor improvements suggested"
        assert mock_achat.call_count == 1


@pytest.mark.asyncio
async def test_generate_pr_review_function(mocker, sample_repository, sample_pull_request):
    mocker.patch(
        "lampe.review.workflows.pr_review.multi_agent_pipeline.list_changed_files",
        return_value="src/example.py | +10 -5",
    )

    with patch("llama_index.llms.litellm.LiteLLM.achat") as mock_achat:
        mock_response = MagicMock()
        mock_response.message.content = """{
          "reviews": [
            {
              "file_path": "src/example.py",
              "line_comments": {
                "15": "Consider adding null check here"
              },
              "summary": "Good implementation"
            }
          ]
        }"""
        mock_achat.return_value = mock_response

        result = await generate_multi_agent_pr_review(
            repository=sample_repository,
            pull_request=sample_pull_request,
            review_depth=ReviewDepth.BASIC,
            custom_guidelines=["Focus on security issues"],
        )

        assert len(result.reviews) == 1
        assert result.reviews[0]["file_path"] == "src/example.py"
        assert result.reviews[0]["line_comments"]["15"] == "Consider adding null check here"
        assert result.reviews[0]["summary"] == "Good implementation"
