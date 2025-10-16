import json
from unittest.mock import MagicMock, patch

import pytest

from lampe.core.data_models import PullRequest, Repository
from lampe.describe.workflows.pr_description.generation import generate_pr_description
from lampe.describe.workflows.pr_description.generation_prompt import PRDescriptionOutput


@pytest.fixture
def generate_task_input():
    fixture_path = "packages/lampe-describe/tests/fixtures/describe/pr_description/generate_task_input.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def file_content_base():
    return "def old_feature():\n    pass\n" + "new line" * 1000


@pytest.fixture
def file_content_head():
    return "def new_feature():\n    pass\n"


@pytest.fixture
def expected_output():
    mock = MagicMock()
    mock.message.content = """### What change is being made?

Added a new feature.

### Why are these changes being made?

To improve the product.
"""
    return mock


@pytest.mark.asyncio
async def test_description_generation_integration_real_git(
    mocker, generate_task_input, file_content_base, file_content_head, expected_output, git_repo_with_branches
):
    # Setup repo with a file that changes between base and head
    file_path = "src/new_feature.py"
    repo_path, base_commit_hash, head_commit_hash = git_repo_with_branches(
        file_path, file_content_base, file_content_head
    )

    repo = Repository(local_path=repo_path)
    pr_data = generate_task_input["pull_request"]
    pr = PullRequest(
        number=pr_data["number"],
        title=pr_data["title"],
        base_commit_hash=base_commit_hash,
        base_branch_name=pr_data["base_branch_name"],
        head_commit_hash=head_commit_hash,
        head_branch_name=pr_data["head_branch_name"],
    )

    # Only mock the LLM, not the diff
    with patch("llama_index.llms.litellm.LiteLLM.achat", return_value=expected_output):
        result = await generate_pr_description(repo, pr)
        assert isinstance(result, PRDescriptionOutput)
        assert "What change is being made?" in result.description
        assert "Why are these changes being made?" in result.description
        assert "Added a new feature" in result.description


@pytest.mark.asyncio
async def test_description_generation_truncation_integration_real_git(
    mocker, generate_task_input, file_content_base, file_content_head, git_repo_with_branches
):
    MAX_TOKENS = 1
    # Setup repo with a file that changes between base and head
    file_path = "src/new_feature.py"
    repo_path, base_commit_hash, head_commit_hash = git_repo_with_branches(
        file_path, file_content_base, file_content_head
    )

    repo = Repository(local_path=repo_path)
    pr_data = generate_task_input["pull_request"]
    pr = PullRequest(
        number=pr_data["number"],
        title=pr_data["title"],
        base_commit_hash=base_commit_hash,
        base_branch_name=pr_data["base_branch_name"],
        head_commit_hash=head_commit_hash,
        head_branch_name=pr_data["head_branch_name"],
    )

    captured_prompt = {}

    async def dummy_achat(messages, **kwargs):
        for msg in messages:
            if msg.role.value == "user":
                captured_prompt["prompt"] = msg.content
        return MagicMock(message=MagicMock(role="assistant", content="irrelevant"))

    with patch("llama_index.llms.litellm.LiteLLM.achat", side_effect=dummy_achat):
        await generate_pr_description(repo, pr, truncation_tokens=MAX_TOKENS)
        prompt = captured_prompt["prompt"]
        assert len(prompt) < 400  # Should be very short (diff should be more than 1000 lines without truncation)
        # Should not contain both function names
        assert not ("new_feature" in prompt and "old_feature" in prompt)
        assert "<code_changes>" in prompt
