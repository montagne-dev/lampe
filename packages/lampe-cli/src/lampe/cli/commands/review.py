from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from lampe.cli.orchestrators.pr_review import (
    AgenticReviewAdapter,
    DiffByDiffReviewAdapter,
    PRReviewConfig,
    PRReviewOrchestratorWorkflow,
    PRReviewStart,
)
from lampe.cli.providers.base import Provider
from lampe.core import initialize
from lampe.core.data_models import PullRequest, Repository
from lampe.review.workflows.pr_review.agents import DefaultAgent
from lampe.review.workflows.pr_review.data_models import ReviewDepth


def review(
    repo: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True, readable=True),
    repo_full_name: str | None = typer.Option(None, help="Repository full name (e.g. owner/repo)"),
    base: str = typer.Option(..., help="Base commit SHA"),
    head: str = typer.Option(..., help="Head commit SHA"),
    title: str = typer.Option("Pull Request", help="PR title (local runs)"),
    output: str = typer.Option("auto", help="Output provider (auto|console|github|gitlab|bitbucket)"),
    review_depth: ReviewDepth = typer.Option(ReviewDepth.STANDARD, help="Review depth (basic|standard|comprehensive)"),
    variant: str = typer.Option("multi-agent", help="Review variant (multi-agent|diff-by-diff)"),
    guidelines: list[str] | None = typer.Option(None, "--guideline", help="Custom review guidelines (can be repeated)"),
    files_exclude: list[str] | None = typer.Option(None, "--exclude"),
    timeout: int | None = typer.Option(None, "--timeout-seconds"),
    verbose: bool = typer.Option(False, "--verbose/--no-verbose"),
):
    """Generate a PR code review and deliver it to the specified output provider."""
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

    generator = DiffByDiffReviewAdapter() if variant == "diff-by-diff" else AgenticReviewAdapter()
    pr_cfg = PRReviewConfig(
        review_depth=review_depth,
        custom_guidelines=guidelines,
        files_exclude_patterns=files_exclude,
        agents_required=[DefaultAgent],
        timeout=timeout,
        verbose=verbose,
    )

    async def _run():
        workflow_task = PRReviewOrchestratorWorkflow(
            provider=provider, generator=generator, timeout=timeout, verbose=verbose
        )
        await workflow_task.run(start_event=PRReviewStart(repository=repo_model, pull_request=pr_model, config=pr_cfg))

    asyncio.run(_run())
