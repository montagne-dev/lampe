import tempfile
from unittest.mock import MagicMock, patch

import pytest

from lampe.core.data_models import PullRequest, Repository
from lampe.describe.workflows.pr_description.generation import (
    PRDescriptionStartEvent,
    PRDescriptionWorkflow,
)
from lampe.describe.workflows.pr_description.generation_prompt import PRDescriptionOutput


@pytest.fixture
def mock_llm_response():
    mock = MagicMock()
    mock.message.content = """### What change is being made?

Added a new feature.

### Why are these changes being made?

To improve the product.
"""
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
async def test_pr_description_workflow_run(mocker, mock_llm_response, sample_repository, sample_pull_request):
    mocker.patch(
        "lampe.describe.workflows.pr_description.generation.get_diff_between_commits",
        return_value="+ new code\n- old code",
    )
    mocker.patch(
        "lampe.describe.workflows.pr_description.generation.truncate_to_token_limit", side_effect=lambda x, y: x
    )

    workflow = PRDescriptionWorkflow(timeout=None, verbose=False)

    start_event = PRDescriptionStartEvent(
        pr_title=sample_pull_request.title,
        repository=sample_repository,
        pull_request=sample_pull_request,
        files_exclude_patterns=["*.md"],
    )
    with patch("llama_index.llms.litellm.LiteLLM.achat", return_value=mock_llm_response) as mock_achat:
        result = await workflow.run(start_event=start_event)
        assert isinstance(result, PRDescriptionOutput)
        assert "What change is being made?" in result.description
        assert "Why are these changes being made?" in result.description
        assert mock_achat.call_count == 1
        assert len(mock_achat.call_args) == 2


@pytest.mark.asyncio
async def test_pr_description_workflow_run_with_md_code_block(
    mocker, mock_llm_response, sample_repository, sample_pull_request
):
    mocker.patch(
        "lampe.describe.workflows.pr_description.generation.get_diff_between_commits",
        return_value="+ new code\n- old code",
    )
    mocker.patch(
        "lampe.describe.workflows.pr_description.generation.truncate_to_token_limit", side_effect=lambda x, y: x
    )
    mock_llm_response.message.content = """
```md
### What change is being made?

Added a new feature.
```
    """
    workflow = PRDescriptionWorkflow(timeout=None, verbose=False)

    start_event = PRDescriptionStartEvent(
        pr_title=sample_pull_request.title,
        repository=sample_repository,
        pull_request=sample_pull_request,
        files_exclude_patterns=["*.md"],
    )
    with patch("llama_index.llms.litellm.LiteLLM.achat", return_value=mock_llm_response) as mock_achat:
        result = await workflow.run(start_event=start_event)
        assert isinstance(result, PRDescriptionOutput)
        assert "```md" not in result.description
        assert "What change is being made?" in result.description
        assert "Added a new feature." in result.description
        assert mock_achat.call_count == 1
        assert len(mock_achat.call_args) == 2


@pytest.mark.asyncio
async def test_pr_description_workflow_step_by_step(mocker, mock_llm_response, sample_repository, sample_pull_request):
    mocker.patch(
        "lampe.describe.workflows.pr_description.generation.get_diff_between_commits",
        return_value="+ new code\n- old code",
    )
    mocker.patch(
        "lampe.describe.workflows.pr_description.generation.truncate_to_token_limit", side_effect=lambda x, y: x
    )

    workflow = PRDescriptionWorkflow(timeout=None, verbose=False)

    start_event = PRDescriptionStartEvent(
        pr_title=sample_pull_request.title,
        repository=sample_repository,
        pull_request=sample_pull_request,
        files_exclude_patterns=["*.md"],
    )
    prompt_event = await workflow.prepare_diff_and_prompt(ev=start_event)
    assert "Add new feature" in prompt_event.formatted_prompt
    assert "+ new code\n- old code" in prompt_event.formatted_prompt

    with patch("llama_index.llms.litellm.LiteLLM.achat", return_value=mock_llm_response):
        result = await workflow.generate_description(ev=prompt_event)
        assert isinstance(result.result, PRDescriptionOutput)
        assert "What change is being made?" in result.result.description
        assert "Why are these changes being made?" in result.result.description


@pytest.mark.asyncio
async def test_pr_description_workflow_step_by_step_with_truncation(
    mocker, mock_llm_response, sample_repository, sample_pull_request
):
    MAX_TOKENS = 1
    long_diff = "+" + "\n+".join(["new line " + str(i) for i in range(10000)])

    mocker.patch("lampe.describe.workflows.pr_description.generation.get_diff_between_commits", return_value=long_diff)

    workflow = PRDescriptionWorkflow(truncation_tokens=MAX_TOKENS, timeout=None, verbose=False)

    start_event = PRDescriptionStartEvent(
        pr_title=sample_pull_request.title,
        repository=sample_repository,
        pull_request=sample_pull_request,
        files_exclude_patterns=["*.md"],
    )
    prompt_event = await workflow.prepare_diff_and_prompt(ev=start_event)
    assert "Add new feature" in prompt_event.formatted_prompt
    assert "<code_changes>\n+" in prompt_event.formatted_prompt

    with patch("llama_index.llms.litellm.LiteLLM.achat", return_value=mock_llm_response):
        result = await workflow.generate_description(ev=prompt_event)
        assert isinstance(result.result, PRDescriptionOutput)
        assert "What change is being made?" in result.result.description
        assert "Why are these changes being made?" in result.result.description
