from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from llama_index.core.workflow import Event, StartEvent, StopEvent, Workflow, step

from lampe.cli.providers.base import Provider, PRReviewPayload
from lampe.core.data_models import PullRequest, Repository
from lampe.review.workflows.pr_review.agents.specialized_agent_base import SpecializedReviewAgent
from lampe.review.workflows.pr_review.data_models import AgentReviewOutput, ReviewDepth
from lampe.review.workflows.pr_review.multi_agent_pipeline import PRReviewComplete, generate_multi_agent_pr_review


class PRReviewGenerator(Protocol):
    async def generate(
        self,
        repository: Repository,
        pull_request: PullRequest,
        review_depth: ReviewDepth = ReviewDepth.STANDARD,
        custom_guidelines: list[str] | None = None,
        files_exclude_patterns: list[str] | None = None,
        agents_required: list[type[SpecializedReviewAgent]] | None = None,
        timeout: int | None = None,
        verbose: bool = False,
    ) -> PRReviewComplete:  # expects .reviews
        ...


@dataclass
class PRReviewConfig:
    review_depth: ReviewDepth = ReviewDepth.STANDARD
    custom_guidelines: list[str] | None = None
    agents_required: list[type[SpecializedReviewAgent]] | None = None
    files_exclude_patterns: list[str] | None = None
    timeout: int | None = None
    verbose: bool = False


class AgenticReviewAdapter:
    async def generate(
        self,
        repository: Repository,
        pull_request: PullRequest,
        review_depth: ReviewDepth = ReviewDepth.STANDARD,
        custom_guidelines: list[str] | None = None,
        files_exclude_patterns: list[str] | None = None,
        agents_required: list[type[SpecializedReviewAgent]] | None = None,
        timeout: int | None = None,
        verbose: bool = False,
    ) -> PRReviewComplete:
        result: PRReviewComplete = await generate_multi_agent_pr_review(
            repository=repository,
            pull_request=pull_request,
            review_depth=review_depth,
            custom_guidelines=custom_guidelines,
            files_exclude_patterns=files_exclude_patterns,
            agents_required=agents_required,
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
            agents_required=ev.config.agents_required,
            timeout=ev.config.timeout,
            verbose=ev.config.verbose,
        )

        return PRReviewResult(result=res.output)

    @step
    async def deliver(self, ev: PRReviewResult) -> StopEvent:
        self.provider.deliver_pr_review(PRReviewPayload(reviews=ev.result))
        return StopEvent(result=ev.result)
