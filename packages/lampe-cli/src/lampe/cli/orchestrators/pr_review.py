from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from llama_index.core.workflow import Event, StartEvent, StopEvent, Workflow, step

from lampe.cli.providers.base import Provider, PRReviewPayload
from lampe.core.data_models import PullRequest, Repository
from lampe.review.workflows.agentic_review import AgenticReviewComplete, generate_agentic_pr_review
from lampe.review.workflows.pr_review.data_models import AgentReviewOutput, ReviewDepth


class PRReviewGenerator(Protocol):
    async def generate(
        self,
        repository: Repository,
        pull_request: PullRequest,
        review_depth: ReviewDepth = ReviewDepth.STANDARD,
        custom_guidelines: list[str] | None = None,
        files_exclude_patterns: list[str] | None = None,
        timeout: int | None = None,
        verbose: bool = False,
    ) -> AgenticReviewComplete: ...


@dataclass
class PRReviewConfig:
    review_depth: ReviewDepth = ReviewDepth.STANDARD
    custom_guidelines: list[str] | None = None
    files_exclude_patterns: list[str] | None = None
    timeout: int | None = None
    verbose: bool = False


class AgenticOrchestratorAdapter:
    """Uses the agentic orchestrator workflow (intent, skills, validation agents)."""

    async def generate(
        self,
        repository: Repository,
        pull_request: PullRequest,
        review_depth: ReviewDepth = ReviewDepth.STANDARD,
        custom_guidelines: list[str] | None = None,
        files_exclude_patterns: list[str] | None = None,
        timeout: int | None = None,
        verbose: bool = False,
    ) -> AgenticReviewComplete:
        result = await generate_agentic_pr_review(
            repository=repository,
            pull_request=pull_request,
            review_depth=review_depth,
            custom_guidelines=custom_guidelines,
            files_exclude_patterns=files_exclude_patterns,
            timeout=timeout,
            verbose=verbose,
        )
        return result


class PRReviewStart(StartEvent):
    repository: Repository
    pull_request: PullRequest
    config: PRReviewConfig


class PRReviewResult(Event):
    result: list[AgentReviewOutput]


class PRReviewOrchestratorWorkflow(Workflow):
    def __init__(self, provider: Provider, generator: PRReviewGenerator, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.provider = provider
        self.generator = generator

    @step
    async def run_generation(self, ev: PRReviewStart) -> PRReviewResult:
        res = await self.generator.generate(
            repository=ev.repository,
            pull_request=ev.pull_request,
            review_depth=ev.config.review_depth,
            custom_guidelines=ev.config.custom_guidelines,
            files_exclude_patterns=ev.config.files_exclude_patterns,
            timeout=ev.config.timeout,
            verbose=ev.config.verbose,
        )

        return PRReviewResult(result=res.output)

    @step
    async def deliver(self, ev: PRReviewResult) -> StopEvent:
        self.provider.deliver_pr_review(PRReviewPayload(reviews=ev.result))
        return StopEvent(result=ev.result)
