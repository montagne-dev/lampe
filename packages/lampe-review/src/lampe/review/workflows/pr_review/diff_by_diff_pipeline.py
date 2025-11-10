"""Diff-by-diff parallel review pipeline using BaseParallelWorkflow."""

import logging
from typing import Any

from workflows import Context, Workflow, step
from workflows.events import Event, StartEvent, StopEvent

from lampe.core.data_models import PullRequest, Repository
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.core.tools.repository.diff import (
    FileDiffInfo,
    list_changed_files,
    list_changed_files_as_objects,
)
from lampe.core.workflows.base_parallel import BaseParallelWorkflow, ParallelStartEvent
from lampe.review.workflows.pr_review.agents.diff_focused_agent import DiffFocusedAgent
from lampe.review.workflows.pr_review.agents.specialized_agent_base import (
    SpecializedAgentComplete,
    SpecializedAgentStart,
)
from lampe.review.workflows.pr_review.data_models import (
    AgentReviewInput,
    AgentReviewOutput,
    PRReviewInput,
    ReviewDepth,
)
from lampe.review.workflows.pr_review.llm_aggregation_step import (
    LLMAggregationCompleteEvent,
    LLMAggregationStartEvent,
    LLMAggregationWorkflow,
)
from lampe.review.workflows.pr_review.multi_agent_pipeline import PRReviewComplete


class DiffByDiffStartEvent(StartEvent):
    """Start event for diff-by-diff pipeline workflow."""

    input: PRReviewInput


class ParallelDiffReviewsCompleteEvent(Event):
    """Event when all parallel diff reviews are complete."""

    agent_reviews: list[AgentReviewOutput]
    files_changed: str


class DiffReviewWrapperWorkflow(Workflow):
    """Wrapper workflow to run a single diff-focused agent review."""

    def __init__(self, timeout: int | None = None, verbose: bool = False, *args: Any, **kwargs: Any):
        super().__init__(*args, timeout=timeout, verbose=verbose, **kwargs)
        self.timeout = timeout
        self.verbose = verbose
        self.logger = logging.getLogger(name=LAMPE_LOGGER_NAME)

    @step
    async def run_agent_review(self, ev: SpecializedAgentStart) -> StopEvent:
        """Run a single agent review and return the result."""
        agent = DiffFocusedAgent(timeout=self.timeout, verbose=self.verbose)
        try:
            agent_output: SpecializedAgentComplete = await agent.run(start_event=ev)
            return StopEvent(result=agent_output.review_output)
        except Exception as e:
            self.logger.exception(f"Failed to run agent review: {e}")
            # Return None to indicate failure
            return StopEvent(result=None)


class DiffByDiffPipelineWorkflow(Workflow):
    """Workflow that reviews each file diff in parallel, then aggregates results with LLM."""

    def __init__(
        self,
        timeout: int | None = None,
        verbose: bool = False,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, timeout=timeout, verbose=verbose, **kwargs)
        self.verbose = verbose
        self.timeout = timeout
        self.logger = logging.getLogger(name=LAMPE_LOGGER_NAME)
        self.aggregation_workflow = LLMAggregationWorkflow(timeout=timeout, verbose=verbose)
        # Create parallel workflow with wrapper as inner workflow
        self.parallel_workflow = BaseParallelWorkflow(
            inner=DiffReviewWrapperWorkflow(timeout=timeout, verbose=verbose), timeout=timeout, verbose=verbose
        )

    @step
    async def start_pipeline(self, ctx: Context, ev: DiffByDiffStartEvent) -> ParallelDiffReviewsCompleteEvent | None:
        """Start the diff-by-diff review pipeline."""
        # Get list of changed files as objects
        file_diffs: list[FileDiffInfo] = list_changed_files_as_objects(
            base_reference=ev.input.pull_request.base_commit_hash,
            head_reference=ev.input.pull_request.head_commit_hash,
            repo_path=ev.input.repository.local_path,
        )

        # Apply file exclusion patterns if provided
        if ev.input.files_exclude_patterns:
            from fnmatch import fnmatch

            filtered_file_diffs = []
            for file_diff in file_diffs:
                if not any(fnmatch(file_diff.file_path, pattern) for pattern in ev.input.files_exclude_patterns):
                    filtered_file_diffs.append(file_diff)
                elif ev.input.files_reinclude_patterns and any(
                    fnmatch(file_diff.file_path, pattern) for pattern in ev.input.files_reinclude_patterns
                ):
                    filtered_file_diffs.append(file_diff)
            file_diffs = filtered_file_diffs

        if not file_diffs:
            if self.verbose:
                self.logger.debug("No files to review after filtering")
            return ParallelDiffReviewsCompleteEvent(agent_reviews=[], files_changed="")

        if self.verbose:
            self.logger.debug(f"Starting parallel review of {len(file_diffs)} file diffs...")

        # Get formatted files changed string
        files_changed = list_changed_files(
            base_reference=ev.input.pull_request.base_commit_hash,
            head_reference=ev.input.pull_request.head_commit_hash,
            repo_path=ev.input.repository.local_path,
        )

        # Create agent start events for each file diff
        agent_start_events: list[SpecializedAgentStart] = []
        for file_diff in file_diffs:
            agent_input = AgentReviewInput(
                repository=ev.input.repository,
                pull_request=ev.input.pull_request,
                files_changed=files_changed,
                review_depth=ev.input.review_depth,
                custom_guidelines=ev.input.custom_guidelines,
                target_file_path=file_diff.file_path,
            )
            agent_start_events.append(SpecializedAgentStart(input=agent_input))

        # Run parallel workflow
        # Cast to list[Event] since SpecializedAgentStart extends Event
        inner_events: list[Event] = agent_start_events  # type: ignore[assignment]
        parallel_results = await self.parallel_workflow.run(start_event=ParallelStartEvent(inner_events=inner_events))

        # Extract results (filter out None for failed reviews)
        # parallel_results is a list of StopEvent results from the wrapper workflow
        agent_reviews: list[AgentReviewOutput] = [
            result for result in parallel_results if result is not None and isinstance(result, AgentReviewOutput)
        ]

        if self.verbose:
            self.logger.debug(f"Completed {len(agent_reviews)} of {len(file_diffs)} parallel reviews")

        return ParallelDiffReviewsCompleteEvent(agent_reviews=agent_reviews, files_changed=files_changed)

    @step
    async def aggregate_reviews(self, ctx: Context, ev: ParallelDiffReviewsCompleteEvent) -> PRReviewComplete:
        """Aggregate and clean reviews using LLM workflow."""
        if not ev.agent_reviews:
            if self.verbose:
                self.logger.debug("No reviews to aggregate")
            return PRReviewComplete(output=[])

        # Run aggregation workflow
        aggregation_result: LLMAggregationCompleteEvent = await self.aggregation_workflow.run(
            start_event=LLMAggregationStartEvent(
                agent_reviews=ev.agent_reviews,
                files_changed=ev.files_changed,
            )
        )

        if self.verbose:
            self.logger.debug(f"Pipeline complete with {len(aggregation_result.aggregated_reviews)} aggregated reviews")

        return PRReviewComplete(output=aggregation_result.aggregated_reviews)


async def generate_diff_by_diff_pr_review(
    repository: Repository,
    pull_request: PullRequest,
    review_depth: ReviewDepth = ReviewDepth.STANDARD,
    custom_guidelines: list[str] | None = None,
    files_exclude_patterns: list[str] | None = None,
    files_reinclude_patterns: list[str] | None = None,
    timeout: int | None = None,
    verbose: bool = False,
) -> PRReviewComplete:
    """Generate a PR review using the diff-by-diff parallel pipeline."""
    if files_exclude_patterns is None:
        files_exclude_patterns = []

    # Create the workflow
    workflow = DiffByDiffPipelineWorkflow(timeout=timeout, verbose=verbose)

    # Create input data
    input_data = PRReviewInput(
        repository=repository,
        pull_request=pull_request,
        review_depth=review_depth,
        custom_guidelines=custom_guidelines,
        files_exclude_patterns=files_exclude_patterns,
        files_reinclude_patterns=files_reinclude_patterns,
        use_multi_agent=False,  # This is a different pipeline
    )

    # Run the workflow
    result: PRReviewComplete = await workflow.run(start_event=DiffByDiffStartEvent(input=input_data))

    return result


def main():
    import asyncio
    import json
    import sys

    from lampe.core import initialize
    from lampe.core.tools.repository.management import clone_repo

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

    result: PRReviewComplete = asyncio.run(
        generate_diff_by_diff_pr_review(
            repository=input.repository,
            pull_request=input.pull_request,
            review_depth=input.review_depth,
            custom_guidelines=input.custom_guidelines,
            files_exclude_patterns=input.files_exclude_patterns,
            files_reinclude_patterns=input.files_reinclude_patterns,
            verbose=True,
        )
    )

    # Output the review in a structured format
    for agent_output in result.output:
        print(f"# Agent: {agent_output.agent_name}")
        print(f"**Focus Areas:** {', '.join(agent_output.focus_areas)}")
        print(f"**Global Summary:** {agent_output.summary}")
        print()

        # Show sources as code blocks
        if agent_output.sources:
            print("## Sources")
            for source in agent_output.sources:
                print(f"### Source: {source.tool_name}")
                print("```")
                print(f"Tool: {source.tool_name}")
                print(f"Arguments: {source.tool_kwargs}")
                print(f"Output: {source.tool_output}")
                print("```")
                print()

        # Show file reviews with line comments and severity
        if agent_output.reviews:
            print("## File Reviews")
            for file_review in agent_output.reviews:
                print(f"### {file_review.file_path}")
                print(f"**Summary:** {file_review.summary}")

                # Show structured comments with severity
                if file_review.structured_comments:
                    print("**Issues Found:**")
                    for comment in file_review.structured_comments:
                        print(f"- Line {comment.line_number} ({comment.severity.upper()}): {comment.comment}")
                        print(f"  Category: {comment.category}")

                # Show legacy line comments if no structured comments
                elif file_review.line_comments:
                    print("**Line Comments:**")
                    for line, comment in file_review.line_comments.items():
                        print(f"- Line {line}: {comment}")

                print()

        print("---")
        print()


if __name__ == "__main__":
    main()
