"""Multi-agent sequential pipeline for PR review using LlamaIndex Workflow."""

import logging
from typing import Any

from llama_index.core.workflow import Context, Event, StartEvent, StopEvent, Workflow, step

from lampe.core.data_models.pull_request import PullRequest
from lampe.core.data_models.repository import Repository
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.core.tools.repository.diff import list_changed_files
from lampe.review.workflows.pr_review.agents import (
    DesignPatternAgent,
)
from lampe.review.workflows.pr_review.aggregator import ReviewAggregator
from lampe.review.workflows.pr_review.data_models import (
    AgentReviewInput,
    AgentReviewOutput,
    PRReviewInput,
    PRReviewOutput,
    ReviewDepth,
)


class MultiAgentStart(StartEvent):
    """Start event for multi-agent PR review workflow."""

    input: PRReviewInput


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

    def __init__(self, timeout: int | None = None, verbose: bool = False, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.timeout = timeout
        self.verbose = verbose
        self.aggregator = ReviewAggregator()

        # Initialize all specialized agents
        self.agents = [
            # SecurityAgent(timeout=timeout, verbose=verbose),
            # APIUsageAgent(timeout=timeout, verbose=verbose),
            DesignPatternAgent(timeout=timeout, verbose=verbose),
            # PerformanceAgent(timeout=timeout, verbose=verbose),
            # CodeQualityAgent(timeout=timeout, verbose=verbose),
            # TestingAgent(timeout=timeout, verbose=verbose),
        ]
        self.logger = logging.getLogger(name=LAMPE_LOGGER_NAME)

    @step
    async def execute_pipeline(self, ctx: Context, ev: MultiAgentStart) -> StopEvent:
        """Execute the complete multi-agent review pipeline."""
        # Get list of changed files
        files_changed = list_changed_files(
            base_reference=ev.input.pull_request.base_commit_hash,
            head_reference=ev.input.pull_request.head_commit_hash,
            repo_path=ev.input.repository.local_path,
        )

        # Collect reviews from all agents
        all_agent_reviews = []

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
                agent_output = await agent.review(agent_input)
                all_agent_reviews.append(agent_output)

                if self.verbose:
                    self.logger.debug(f"✓ {agent.agent_name} completed with {len(agent_output.reviews)} file reviews")

            except Exception as e:
                if self.verbose:
                    self.logger.debug(f"✗ {agent.agent_name} failed: {e}")
                # Continue with other agents even if one fails
                continue

        # Aggregate all reviews
        if self.verbose:
            self.logger.debug("Aggregating reviews from all agents...")

        aggregated_reviews = self.aggregator.aggregate_reviews(all_agent_reviews)

        if self.verbose:
            self.logger.debug(f"✓ Pipeline completed with {len(aggregated_reviews)} aggregated reviews")

        return StopEvent(result=PRReviewOutput(reviews=aggregated_reviews))


async def generate_multi_agent_pr_review(
    repository: Repository,
    pull_request: PullRequest,
    review_depth: ReviewDepth = ReviewDepth.STANDARD,
    custom_guidelines: list[str] | None = None,
    files_exclude_patterns: list[str] | None = None,
    timeout: int | None = None,
    verbose: bool = False,
):
    """Generate a PR review using the multi-agent LlamaIndex workflow."""
    if files_exclude_patterns is None:
        files_exclude_patterns = []

    # Create the LlamaIndex workflow
    workflow = MultiAgentPipelineWorkflow(timeout=timeout, verbose=verbose)

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
    result = await workflow.run(start_event=MultiAgentStart(input=input_data))
    print("Workflow result: %s", result)
    return result
