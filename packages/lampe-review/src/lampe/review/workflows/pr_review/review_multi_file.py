import asyncio
import json
from typing import Any

from workflows.context import Context

from lampe.core.data_models import PullRequest, Repository
from lampe.core.tools import clone_repo
from lampe.core.tools.llm_integration import git_tools_gpt_5_nano_agent_prompt
from lampe.core.tools.repository.diff import list_changed_files
from lampe.core.workflows.function_calling_agent import FunctionCallingAgent
from lampe.review.workflows.pr_review.data_models import FileReview, PRReviewInput, PRReviewOutput, ReviewDepth
from lampe.review.workflows.pr_review.multi_agent_pipeline import generate_multi_agent_pr_review
from lampe.review.workflows.pr_review.review_multi_file_prompt import (
    PR_REVIEW_CUSTOM_GUIDELINES_SECTION,
    PR_REVIEW_SYSTEM_PROMPT,
    PR_REVIEW_USER_PROMPT,
)


class PRReviewFnAgentWorkflow(FunctionCallingAgent):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # NOTE: this could be dependency injection of the tools to allow caller to customize them.
        tools = git_tools_gpt_5_nano_agent_prompt
        super().__init__(
            *args,
            tools=tools,
            system_prompt=PR_REVIEW_SYSTEM_PROMPT,
            **kwargs,
        )

    def update_tools(self, partial_params: dict[str, Any] | None = None) -> None:
        for tool in self.tools:
            if hasattr(tool, "partial_params"):
                if partial_params is not None:
                    tool.partial_params = partial_params
                else:
                    tool.partial_params = {}

    def _format_custom_guidelines_section(self, custom_guidelines: list[str] | None) -> str:
        """Format custom guidelines section for the user prompt."""
        if not custom_guidelines:
            return ""

        guidelines_text = "\n".join([f"- {guideline}" for guideline in custom_guidelines])
        return PR_REVIEW_CUSTOM_GUIDELINES_SECTION.format(guidelines_text=guidelines_text)

    async def execute(self, input: PRReviewInput) -> Any:
        files_changed = list_changed_files(
            base_reference=input.pull_request.base_commit_hash,
            head_reference=input.pull_request.head_commit_hash,
            repo_path=input.repository.local_path,
        )

        custom_guidelines_section = self._format_custom_guidelines_section(input.custom_guidelines)

        query = PR_REVIEW_USER_PROMPT.format(
            pull_request=input.pull_request,
            files_changed=files_changed,
            review_depth=input.review_depth.value,
            custom_guidelines_section=custom_guidelines_section,
        )

        self.update_tools(partial_params={"repo_path": input.repository.local_path})
        response = await super().run(input=query, ctx=Context(self))

        # Parse the JSON response from the LLM
        try:
            review_data = json.loads(response.result["response"].message.content)
            reviews = []
            for review_item in review_data.get("reviews", []):
                reviews.append(FileReview.model_validate(review_item))
            return PRReviewOutput(reviews=reviews)
        except (json.JSONDecodeError, KeyError):
            # Fallback: create a single review with the raw response
            return PRReviewOutput(
                reviews=[
                    FileReview(
                        file_path="general",
                        line_comments={},
                        summary=response.result["response"].message.content,
                    )
                ]
            )


async def generate_pr_review(
    repository: Repository,
    pull_request: PullRequest,
    review_depth: ReviewDepth = ReviewDepth.STANDARD,
    custom_guidelines: list[str] | None = None,
    files_exclude_patterns: list[str] | None = None,
    timeout: int | None = None,
    verbose: bool = False,
    use_multi_agent: bool = True,
):
    """Generate a PR review using either multi-agent or single-agent workflow."""
    if files_exclude_patterns is None:
        files_exclude_patterns = []

    if use_multi_agent:
        # Use multi-agent pipeline
        return await generate_multi_agent_pr_review(
            repository=repository,
            pull_request=pull_request,
            review_depth=review_depth,
            custom_guidelines=custom_guidelines,
            files_exclude_patterns=files_exclude_patterns,
            timeout=timeout,
            verbose=verbose,
        )
    else:
        # Use single-agent workflow (backward compatibility)
        workflow = PRReviewFnAgentWorkflow(timeout=timeout, verbose=verbose)
        result = await workflow.execute(
            input=PRReviewInput(
                repository=repository,
                pull_request=pull_request,
                review_depth=review_depth,
                custom_guidelines=custom_guidelines,
                files_exclude_patterns=files_exclude_patterns,
                use_multi_agent=False,
            )
        )
        return result


def main():
    import sys

    from lampe.core import initialize

    initialize()
    if len(sys.argv) < 2:
        print("Usage: pr_review_generation <input_json_file>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    repository_path = clone_repo(
        data["repository"]["url"],
        head_ref=data["pull_request"]["head_commit_hash"],
        base_ref=data["pull_request"]["base_commit_hash"],
    )
    data["repository"] = dict(local_path=repository_path)

    input = PRReviewInput.model_validate(data)

    result = asyncio.run(
        generate_pr_review(
            repository=input.repository,
            pull_request=input.pull_request,
            review_depth=input.review_depth,
            custom_guidelines=input.custom_guidelines,
            files_exclude_patterns=input.files_exclude_patterns,
        )
    )

    # Output the review in a structured format
    for review in result.reviews:
        print(f"## {review.file_path}")
        print(f"**Summary:** {review.summary}")
        if review.line_comments:
            print("**Line Comments:**")
            for line, comment in review.line_comments.items():
                print(f"- Line {line}: {comment}")
        print()


if __name__ == "__main__":
    main()
