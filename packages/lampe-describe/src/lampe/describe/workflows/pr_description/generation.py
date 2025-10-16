import asyncio

from llama_index.core.prompts import ChatMessage, MessageRole
from llama_index.core.workflow import Event, StartEvent, StopEvent, Workflow, step
from llama_index.llms.litellm import LiteLLM

from lampe.core.data_models import PullRequest, Repository
from lampe.core.llmconfig import MODELS
from lampe.core.parsers.markdown_code_block_remover_output import MarkdownCodeBlockRemoverOutputParser
from lampe.core.tools.repository import clone_repo, get_diff_between_commits
from lampe.core.utils.token import truncate_to_token_limit
from lampe.describe.workflows.pr_description.data_models import PRDescriptionInput
from lampe.describe.workflows.pr_description.generation_prompt import (
    SYSTEM_PR_DESCRIPTION_MESSAGE,
    USER_PR_DESCRIPTION_MESSAGE,
    PRDescriptionOutput,
)

# NOTE: Max tokens for the diff content, by default 100k to avoid spending too much
MAX_TOKENS = 100_000


class PRDescriptionStartEvent(StartEvent):
    pr_title: str
    repository: Repository
    pull_request: PullRequest
    files_exclude_patterns: list[str] | None = None
    files_reinclude_patterns: list[str] | None = None


class PRDescriptionPromptEvent(Event):
    formatted_prompt: str


class PRDescriptionWorkflow(Workflow):
    """A workflow that generates a PR description.

    Based on the pull request's diff generate a clear,
    concise description explaining what are the changes being made and why.

    Parameters
    ----------
    truncation_tokens
        Maximum number of tokens to use for the diff content, by default MAX_TOKENS
    """

    def __init__(self, truncation_tokens=MAX_TOKENS, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.llm = LiteLLM(model=MODELS.GPT_5_NANO_2025_08_07, temperature=1.0)
        self.truncation_tokens = truncation_tokens
        self.output_parser = MarkdownCodeBlockRemoverOutputParser()

    @step
    async def prepare_diff_and_prompt(self, ev: PRDescriptionStartEvent) -> PRDescriptionPromptEvent:
        """Prepare the diff and prompt for the LLM.

        This step prepares the diff and prompt for the LLM.
        It truncates the diff to the maximum number of tokens and formats the prompt.
        The diff is filtered using files_exclude_patterns, files_include_patterns and files_reinclude_patterns.
        The files_reinclude_patterns allow overriding files_exclude_patterns, which is useful for patterns like
        "!readme.txt" that should override "*.txt" exclusions.

        Parameters
        ----------
        ev
            The start event containing the PR details.

        Returns
        -------
        :
            The prompt event containing the prepared diff and prompt.
        """
        repo_path = ev.repository.local_path
        base_hash = ev.pull_request.base_commit_hash
        head_hash = ev.pull_request.head_commit_hash
        diff = get_diff_between_commits(
            base_hash, head_hash, files_exclude_patterns=ev.files_exclude_patterns, repo_path=repo_path
        )
        diff = truncate_to_token_limit(diff, self.truncation_tokens)
        formatted_prompt = USER_PR_DESCRIPTION_MESSAGE.format(
            pr_title=ev.pr_title,
            pull_request_diff=diff,
        )
        return PRDescriptionPromptEvent(formatted_prompt=formatted_prompt)

    @step
    async def generate_description(self, ev: PRDescriptionPromptEvent) -> StopEvent:
        """Generate a PR description.

        This step generates a PR description using the LLM.
        It uses the truncated diff of all the changes between 2 commits.

        Parameters
        ----------
        ev
            The prompt event containing the prepared diff and prompt.

        Returns
        -------
        :
            The stop event containing the generated description.
        """
        response = await self.llm.achat(
            messages=[
                ChatMessage(role=MessageRole.SYSTEM, content=SYSTEM_PR_DESCRIPTION_MESSAGE),
                ChatMessage(role=MessageRole.USER, content=ev.formatted_prompt),
            ]
        )

        description = self.output_parser.parse(response.message.content or "")
        return StopEvent(result=PRDescriptionOutput(description=description))


async def generate_pr_description(
    repository: Repository,
    pull_request: PullRequest,
    files_exclude_patterns: list[str] | None = None,
    files_reinclude_patterns: list[str] | None = None,
    truncation_tokens: int = MAX_TOKENS,
    timeout: int | None = None,
    verbose: bool = False,
    metadata: dict | None = None,
) -> PRDescriptionOutput:
    """Generate a PR description.

    This function generates a PR description for a given pull request.
    It uses the PRDescriptionWorkflow to generate the description.

    Parameters
    ----------
    repository
        The repository to generate the PR description for.
    pull_request
        The pull request to generate the PR description for.
    files_exclude_patterns
        The glob matching patterns to exclude from the diff, by default None
    files_reinclude_patterns
        The glob matching patterns to re-include in the diff, by default None
    truncation_tokens
        The maximum number of tokens to use for the diff content, by default MAX_TOKENS
    timeout
        The timeout for the workflow, by default None
    verbose
        Whether to print verbose output, by default False
    metadata
        The metadata to use for the workflow, by default None

    Returns
    -------
    :
        The output containing the generated description.
    """
    if files_exclude_patterns is None:
        files_exclude_patterns = []
    workflow = PRDescriptionWorkflow(truncation_tokens=truncation_tokens, timeout=timeout, verbose=verbose)
    result = await workflow.run(
        start_event=PRDescriptionStartEvent(
            pr_title=pull_request.title,
            repository=repository,
            pull_request=pull_request,
            files_exclude_patterns=files_exclude_patterns,
        )
    )
    return result


def main():
    import json
    import sys

    from lampe.core import initialize

    initialize()
    if len(sys.argv) < 2:
        print("Usage: pr_description_generation <input_json_file>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    repository_path = clone_repo(
        data["repository"]["url"],
        head_ref=data["pull_request"]["head_commit_hash"],
    )
    data["repository"] = dict(local_path=repository_path)

    input = PRDescriptionInput.model_validate(data)

    result = asyncio.run(
        generate_pr_description(
            repository=input.repository,
            pull_request=input.pull_request,
            files_exclude_patterns=input.files_exclude_patterns,
            files_reinclude_patterns=input.files_reinclude_patterns,
        )
    )
    print(result.description)
