import tempfile
from unittest.mock import MagicMock, patch

import pytest

from lampe.core.data_models import PullRequest, Repository
from lampe.review.workflows.pr_review.data_models import ReviewDepth
from lampe.review.workflows.pr_review.review_multi_file import (
    PRReviewFnAgentWorkflow,
    generate_pr_review,
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
        "lampe.review.workflows.pr_review.review_multi_file.list_changed_files",
        return_value="src/example.py | +10 -5",
    )

    workflow = PRReviewFnAgentWorkflow(timeout=None, verbose=False)

    with patch("llama_index.llms.litellm.LiteLLM.achat", return_value=mock_llm_response) as mock_achat:
        result = await workflow.execute(
            input={
                "repository": sample_repository,
                "pull_request": sample_pull_request,
                "review_depth": ReviewDepth.STANDARD,
                "custom_guidelines": None,
                "files_exclude_patterns": None,
            }
        )
        assert result.reviews[0]["file_path"] == "src/example.py"
        assert result.reviews[0]["line_comments"]["15"] == "Consider adding null check here"
        assert result.reviews[0]["summary"] == "Overall good implementation, minor improvements suggested"
        assert mock_achat.call_count == 1


@pytest.mark.asyncio
async def test_generate_pr_review_function(mocker, sample_repository, sample_pull_request):
    mocker.patch(
        "lampe.review.workflows.pr_review.review_multi_file.list_changed_files",
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

        result = await generate_pr_review(
            repository=sample_repository,
            pull_request=sample_pull_request,
            review_depth=ReviewDepth.BASIC,
            custom_guidelines=["Focus on security issues"],
        )

        assert len(result.reviews) == 1
        assert result.reviews[0]["file_path"] == "src/example.py"
        assert result.reviews[0]["line_comments"]["15"] == "Consider adding null check here"
        assert result.reviews[0]["summary"] == "Good implementation"


@pytest.mark.asyncio
async def test_custom_guidelines_formatting(mocker, sample_repository, sample_pull_request):
    mocker.patch(
        "lampe.review.workflows.pr_review.review_multi_file.list_changed_files",
        return_value="src/example.py | +10 -5",
    )

    workflow = PRReviewFnAgentWorkflow(timeout=None, verbose=False)

    # Test that custom guidelines are properly formatted
    guidelines = ["Focus on security vulnerabilities", "Check for performance issues"]
    custom_guidelines_section = workflow._format_custom_guidelines_section(guidelines)

    assert "Focus on security vulnerabilities" in custom_guidelines_section
    assert "Check for performance issues" in custom_guidelines_section
    assert "Focus your review ONLY on these specific guidelines" in custom_guidelines_section


@pytest.mark.asyncio
async def test_no_custom_guidelines_formatting(sample_repository, sample_pull_request):
    workflow = PRReviewFnAgentWorkflow(timeout=None, verbose=False)

    # Test that no guidelines returns empty string
    custom_guidelines_section = workflow._format_custom_guidelines_section(None)
    assert custom_guidelines_section == ""

    custom_guidelines_section = workflow._format_custom_guidelines_section([])
    assert custom_guidelines_section == ""


