import asyncio
from typing import Any

from workflows.context import Context

from lampe.core.data_models import PullRequest, Repository
from lampe.core.tools import clone_repo
from lampe.core.tools.llm_integration import git_tools_gpt_5_nano_agent_prompt
from lampe.core.tools.repository.diff import list_changed_files
from lampe.core.workflows.function_calling_agent import FunctionCallingAgent
from lampe.describe.workflows.pr_description.data_models import PRDescriptionInput
from lampe.describe.workflows.pr_description.generation_multi_file_prompt import (
    PR_DESCRIPTION_SYSTEM_PROMPT,
    PR_DESCRIPTION_USER_PROMPT,
    PRDescriptionOutput,
)


class PRDescriptionFnAgentWorkflow(FunctionCallingAgent):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # NOTE: this could be dependency injection of the tools to allow caller to customize them.
        tools = git_tools_gpt_5_nano_agent_prompt
        super().__init__(
            *args,
            tools=tools,
            system_prompt=PR_DESCRIPTION_SYSTEM_PROMPT,
            **kwargs,
        )

    def update_tools(self, partial_params: dict[str, Any] | None = None) -> None:
        for tool in self.tools:
            if hasattr(tool, "partial_params"):
                if partial_params is not None:
                    tool.partial_params = partial_params
                else:
                    tool.partial_params = {}

    async def execute(self, input: PRDescriptionInput) -> Any:
        files_changed = list_changed_files(
            base_reference=input.pull_request.base_commit_hash,
            head_reference=input.pull_request.head_commit_hash,
            repo_path=input.repository.local_path,
        )
        query = PR_DESCRIPTION_USER_PROMPT.format(pull_request=input.pull_request, files_changed=files_changed)

        self.update_tools(partial_params={"repo_path": input.repository.local_path})
        response = await super().run(input=query, ctx=Context(self))
        return PRDescriptionOutput(description=response.result["response"].message.content)


async def generate_pr_description(
    repository: Repository,
    pull_request: PullRequest,
    files_exclude_patterns: list[str] | None = None,
    timeout: int | None = None,
    verbose: bool = False,
):
    if files_exclude_patterns is None:
        files_exclude_patterns = []
    workflow = PRDescriptionFnAgentWorkflow(timeout=timeout, verbose=verbose)
    result = await workflow.execute(
        input=PRDescriptionInput(
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
        base_ref=data["pull_request"]["base_commit_hash"],
    )
    data["repository"] = dict(local_path=repository_path)

    input = PRDescriptionInput.model_validate(data)

    result = asyncio.run(generate_pr_description(input.repository, input.pull_request, input.files_exclude_patterns))
    print(result.description)


if __name__ == "__main__":
    main()
