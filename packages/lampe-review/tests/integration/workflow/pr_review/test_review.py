import tempfile
from unittest.mock import MagicMock, patch

import pytest

from lampe.core.data_models import PullRequest, Repository
from lampe.review.workflows.pr_review.data_models import ReviewDepth
from lampe.review.workflows.pr_review.review_multi_file import generate_pr_review


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
async def test_integration_review_workflow(mocker, sample_repository, sample_pull_request):
    """Integration test for the complete review workflow."""
    # Mock the git tools
    mocker.patch(
        "lampe.review.workflows.pr_review.review_multi_file.list_changed_files",
        return_value="src/example.py | +10 -5",
    )

    # Mock the LLM response
    with patch("llama_index.llms.litellm.LiteLLM.achat") as mock_achat:
        mock_response = MagicMock()
        mock_response.message.content = """{
          "reviews": [
            {
              "file_path": "src/example.py",
              "line_comments": {
                "15": "Consider adding null check here",
                "42": "This could cause performance issues with large datasets"
              },
              "summary": "Overall good implementation, minor improvements suggested"
            },
            {
              "file_path": "tests/test_example.py",
              "line_comments": {
                "8": "Add more test cases for edge cases"
              },
              "summary": "Good test coverage, but could be more comprehensive"
            }
          ]
        }"""
        mock_achat.return_value = mock_response

        result = await generate_pr_review(
            repository=sample_repository,
            pull_request=sample_pull_request,
            review_depth=ReviewDepth.COMPREHENSIVE,
            custom_guidelines=["Focus on security", "Check performance"],
            files_exclude_patterns=["*.md"],
        )

        # Verify the result structure
        assert len(result.reviews) == 2

        # Check first review
        first_review = result.reviews[0]
        assert first_review["file_path"] == "src/example.py"
        assert first_review["line_comments"]["15"] == "Consider adding null check here"
        assert first_review["line_comments"]["42"] == "This could cause performance issues with large datasets"
        assert first_review["summary"] == "Overall good implementation, minor improvements suggested"

        # Check second review
        second_review = result.reviews[1]
        assert second_review["file_path"] == "tests/test_example.py"
        assert second_review["line_comments"]["8"] == "Add more test cases for edge cases"
        assert second_review["summary"] == "Good test coverage, but could be more comprehensive"


@pytest.mark.asyncio
async def test_different_review_depths(mocker, sample_repository, sample_pull_request):
    """Test that different review depths work correctly."""
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
              "line_comments": {},
              "summary": "Basic review completed"
            }
          ]
        }"""
        mock_achat.return_value = mock_response

        # Test basic review
        result_basic = await generate_pr_review(
            repository=sample_repository,
            pull_request=sample_pull_request,
            review_depth=ReviewDepth.BASIC,
        )
        assert len(result_basic.reviews) == 1
        assert result_basic.reviews[0]["summary"] == "Basic review completed"

        # Test standard review
        result_standard = await generate_pr_review(
            repository=sample_repository,
            pull_request=sample_pull_request,
            review_depth=ReviewDepth.STANDARD,
        )
        assert len(result_standard.reviews) == 1

        # Test comprehensive review
        result_comprehensive = await generate_pr_review(
            repository=sample_repository,
            pull_request=sample_pull_request,
            review_depth=ReviewDepth.COMPREHENSIVE,
        )
        assert len(result_comprehensive.reviews) == 1


