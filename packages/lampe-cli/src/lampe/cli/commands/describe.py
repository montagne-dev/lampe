from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from lampe.cli.orchestrators.pr_description import (
    AgenticGeneratorAdapter,
    DefaultGeneratorAdapter,
    PRDescriptionConfig,
    PRDescriptionOrchestratorWorkflow,
    PRDescriptionStart,
)
from lampe.cli.providers.base import Provider
from lampe.core import initialize
from lampe.core.data_models import PullRequest, Repository
from lampe.describe.workflows.pr_description.generation import MAX_TOKENS as DEFAULT_MAX_TOKENS


def describe(
    repo: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True, readable=True),
    repo_full_name: str | None = typer.Option(None, help="Repository full name (e.g. owner/repo)"),
    base: str = typer.Option(..., help="Base commit SHA"),
    head: str = typer.Option(..., help="Head commit SHA"),
    title: str = typer.Option("Pull Request", help="PR title (local runs)"),
    output: str = typer.Option("auto", help="Output provider (auto|console|github|gitlab|bitbucket)"),
    variant: str = typer.Option("default", help="default|agentic"),
    files_exclude: list[str] | None = typer.Option(None, "--exclude"),
    files_reinclude: list[str] | None = typer.Option(None, "--reinclude"),
    truncation_tokens: int = typer.Option(DEFAULT_MAX_TOKENS, "--max-tokens"),
    timeout: int | None = typer.Option(None, "--timeout-seconds"),
    verbose: bool = typer.Option(False, "--verbose/--no-verbose"),
):
    """Generate a PR description and deliver it to the specified output provider."""
    initialize()
    repo_model = Repository(local_path=str(repo), full_name=repo_full_name)
    pr_model = PullRequest(
        number=0,
        title=title,
        body=None,
        base_commit_hash=base,
        base_branch_name="",
        head_commit_hash=head,
        head_branch_name="",
    )

    provider = Provider.create_provider(provider_name=output, repository=repo_model, pull_request=pr_model)

    generator = DefaultGeneratorAdapter() if variant == "default" else AgenticGeneratorAdapter()
    pr_cfg = PRDescriptionConfig(
        files_exclude_patterns=list(files_exclude) if files_exclude else None,
        files_reinclude_patterns=list(files_reinclude) if files_reinclude else None,
        truncation_tokens=truncation_tokens,
        timeout=timeout,
        verbose=verbose,
    )

    async def _run():
        workflow_task = PRDescriptionOrchestratorWorkflow(
            provider=provider, generator=generator, timeout=timeout, verbose=verbose
        )
        await workflow_task.run(
            start_event=PRDescriptionStart(repository=repo_model, pull_request=pr_model, config=pr_cfg)
        )

    asyncio.run(_run())
