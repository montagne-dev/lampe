"""Multi-agent sequential pipeline for PR review using LlamaIndex Workflow."""

import asyncio
import json
import logging
from typing import Any

from workflows import Context, Workflow, step
from workflows.events import Event, StartEvent, StopEvent

from lampe.core.data_models import PullRequest, Repository
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.core.tools import clone_repo
from lampe.core.tools.repository.diff import list_changed_files
from lampe.review.workflows.pr_review.agents import DefaultAgent, DesignPatternAgent
from lampe.review.workflows.pr_review.agents.specialized_agent_base import (
    SpecializedAgentComplete,
    SpecializedAgentStart,
    SpecializedReviewAgent,
)
from lampe.review.workflows.pr_review.aggregator import ReviewAggregator
from lampe.review.workflows.pr_review.data_models import (
    AgentReviewInput,
    AgentReviewOutput,
    PRReviewInput,
    ReviewDepth,
)


class PRReviewStart(StartEvent):
    """Start event for PR review workflow."""

    input: PRReviewInput


class PRReviewComplete(StopEvent):
    """Complete event for PR review workflow."""

    output: list[AgentReviewOutput]


class FilesChangedEvent(Event):
    """Event containing the list of changed files."""

    files_changed: str


class AgentReviewEvent(Event):
    """Event containing agent review results."""

    agent_output: AgentReviewOutput


class AggregationEvent(Event):
    """Event containing aggregated reviews."""

    aggregated_reviews: list


class MultiAgentPipelineWorkflow(Workflow):
    """LlamaIndex Workflow for multi-agent PR review pipeline."""

    def __init__(
        self,
        agents: list[SpecializedReviewAgent],
        timeout: int | None = None,
        verbose: bool = False,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, timeout=timeout, verbose=verbose, **kwargs)
        self.verbose = verbose
        self.aggregator = ReviewAggregator()

        # Initialize all specialized agents
        self.agents = agents or [
            # SecurityAgent(timeout=timeout, verbose=verbose),
            # APIUsageAgent(timeout=timeout, verbose=verbose),
            DesignPatternAgent(timeout=timeout, verbose=verbose),
            # PerformanceAgent(timeout=timeout, verbose=verbose),
            # CodeQualityAgent(timeout=timeout, verbose=verbose),
            # TestingAgent(timeout=timeout, verbose=verbose),
        ]
        self.logger = logging.getLogger(name=LAMPE_LOGGER_NAME)

    @step
    async def execute_pipeline(self, ctx: Context, ev: PRReviewStart) -> PRReviewComplete:
        """Execute the complete multi-agent review pipeline."""
        # Get list of changed files
        files_changed = list_changed_files(
            base_reference=ev.input.pull_request.base_commit_hash,
            head_reference=ev.input.pull_request.head_commit_hash,
            repo_path=ev.input.repository.local_path,
        )

        # Collect reviews from all agents
        all_agent_reviews: list[AgentReviewOutput] = []

        for agent in self.agents:
            if self.verbose:
                self.logger.debug(f"Running {agent.agent_name} review...")

            # Create input for this agent
            agent_input = AgentReviewInput(
                repository=ev.input.repository,
                pull_request=ev.input.pull_request,
                files_changed=files_changed,
                review_depth=ev.input.review_depth,
                custom_guidelines=ev.input.custom_guidelines,
            )

            try:
                # Run the agent
                agent_output: SpecializedAgentComplete = await agent.run(
                    start_event=SpecializedAgentStart(input=agent_input)
                )
                all_agent_reviews.append(agent_output.review_output)

                if self.verbose:
                    self.logger.debug(f"✓ {agent.agent_name} completed with {len(agent_output.reviews)} file reviews")

            except Exception as e:
                if self.verbose:
                    self.logger.debug(f"✗ {agent.agent_name} failed: {e}")
                self.logger.exception(e)
                # Continue with other agents even if one fails
                continue

        # Aggregate all reviews
        if self.verbose:
            self.logger.debug("Aggregating reviews from all agents...")

        # aggregated_reviews = self.aggregator.aggregate_reviews(all_agent_reviews)

        # if self.verbose:
        #     self.logger.debug(f"✓ Pipeline completed with {len(aggregated_reviews)} aggregated reviews")

        return PRReviewComplete(output=all_agent_reviews)


async def generate_multi_agent_pr_review(
    repository: Repository,
    pull_request: PullRequest,
    review_depth: ReviewDepth = ReviewDepth.STANDARD,
    custom_guidelines: list[str] | None = None,
    files_exclude_patterns: list[str] | None = None,
    timeout: int | None = None,
    verbose: bool = False,
    agents_required: list[type[SpecializedReviewAgent]] | None = None,
) -> PRReviewComplete:
    """Generate a PR review using the multi-agent LlamaIndex workflow."""
    if files_exclude_patterns is None:
        files_exclude_patterns = []
    agents = []
    if agents_required:
        agents = [agent(timeout=timeout, verbose=verbose) for agent in agents_required]
    # Create the LlamaIndex workflow
    workflow = MultiAgentPipelineWorkflow(agents=agents, timeout=timeout, verbose=verbose)

    # Create input data
    input_data = PRReviewInput(
        repository=repository,
        pull_request=pull_request,
        review_depth=review_depth,
        custom_guidelines=custom_guidelines,
        files_exclude_patterns=files_exclude_patterns,
        use_multi_agent=True,
    )

    # Run the workflow
    result: PRReviewComplete = await workflow.run(start_event=PRReviewStart(input=input_data))

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
    agents_required: list[type[SpecializedReviewAgent]] = [DefaultAgent]
    result: PRReviewComplete = asyncio.run(
        generate_multi_agent_pr_review(
            repository=input.repository,
            pull_request=input.pull_request,
            review_depth=input.review_depth,
            custom_guidelines=input.custom_guidelines,
            files_exclude_patterns=input.files_exclude_patterns,
            agents_required=agents_required,
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
