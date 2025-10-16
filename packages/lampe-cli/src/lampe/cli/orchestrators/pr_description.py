from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from llama_index.core.workflow import Event, StartEvent, StopEvent, Workflow, step

from lampe.cli.providers.base import PRDescriptionPayload, Provider
from lampe.core.data_models import PullRequest, Repository
from lampe.describe.workflows.pr_description.generation import MAX_TOKENS as DEFAULT_MAX_TOKENS
from lampe.describe.workflows.pr_description.generation import generate_pr_description as generate_default_description
from lampe.describe.workflows.pr_description.generation_multi_file import (
    generate_pr_description as generate_agentic_description,
)


class PRDescriptionGenerator(Protocol):
    async def generate(
        self,
        repository: Repository,
        pull_request: PullRequest,
        files_exclude_patterns: list[str] | None = None,
        files_reinclude_patterns: list[str] | None = None,
        truncation_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: int | None = None,
        verbose: bool = False,
        metadata: dict | None = None,
    ) -> object:  # expects .description
        ...


@dataclass
class PRDescriptionConfig:
    files_exclude_patterns: list[str] | None = None
    files_reinclude_patterns: list[str] | None = None
    truncation_tokens: int = DEFAULT_MAX_TOKENS
    timeout: int | None = None
    verbose: bool = False


class DefaultGeneratorAdapter:
    async def generate(
        self,
        repository: Repository,
        pull_request: PullRequest,
        files_exclude_patterns: list[str] | None = None,
        files_reinclude_patterns: list[str] | None = None,
        truncation_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: int | None = None,
        verbose: bool = False,
        metadata: dict | None = None,
    ) -> object:
        return await generate_default_description(
            repository=repository,
            pull_request=pull_request,
            files_exclude_patterns=files_exclude_patterns,
            files_reinclude_patterns=files_reinclude_patterns,
            truncation_tokens=truncation_tokens,
            timeout=timeout,
            verbose=verbose,
            metadata=metadata,
        )


class AgenticGeneratorAdapter:
    async def generate(
        self,
        repository: Repository,
        pull_request: PullRequest,
        files_exclude_patterns: list[str] | None = None,
        files_reinclude_patterns: list[str] | None = None,
        truncation_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: int | None = None,
        verbose: bool = False,
        metadata: dict | None = None,
    ) -> object:
        # agentic path currently ignores reinclude/truncation/metadata
        return await generate_agentic_description(
            repository=repository,
            pull_request=pull_request,
            files_exclude_patterns=files_exclude_patterns,
            timeout=timeout,
            verbose=verbose,
        )


class PRDescriptionStart(StartEvent):
    repository: Repository
    pull_request: PullRequest
    config: PRDescriptionConfig


class PRDescriptionOrchestratorWorkflow(Workflow):
    def __init__(self, provider: Provider, generator: PRDescriptionGenerator, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.provider = provider
        self.generator = generator

    @step
    async def run_generation(self, ev: PRDescriptionStart) -> Event:
        res = await self.generator.generate(
            repository=ev.repository,
            pull_request=ev.pull_request,
            files_exclude_patterns=ev.config.files_exclude_patterns,
            files_reinclude_patterns=ev.config.files_reinclude_patterns,
            truncation_tokens=ev.config.truncation_tokens,
            timeout=ev.config.timeout,
            verbose=ev.config.verbose,
        )
        return Event(result={"description": getattr(res, "description", "")})

    @step
    async def deliver(self, ev: Event) -> StopEvent:
        desc = ev.result["description"]
        self.provider.deliver_pr_description(PRDescriptionPayload(description=desc))
        return StopEvent(result={"description": desc})
