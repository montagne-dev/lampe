from __future__ import annotations

import sys
from pathlib import Path

import typer

from lampe.cli.providers.base import Provider
from lampe.core import initialize
from lampe.core.data_models import PullRequest, Repository


def check_reviewed(
    repo: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True, readable=True),
    repo_full_name: str | None = typer.Option(None, help="Repository full name (e.g. owner/repo)"),
    output: str = typer.Option("auto", help="Output provider (auto|console|github|gitlab|bitbucket)"),
    pr_number: int | None = typer.Option(None, "--pr", help="Pull request number (required for non-console providers)"),
):
    """Check if the token user has already reviewed this PR.

    Returns exit code 0 if reviewed, 1 if not reviewed.
    """
    initialize()
    repo_model = Repository(local_path=str(repo), full_name=repo_full_name)
    pr_model = PullRequest(
        number=pr_number or 0,
        title="",
        body=None,
        base_commit_hash="",
        base_branch_name="",
        head_commit_hash="",
        head_branch_name="",
    )

    try:
        provider = Provider.create_provider(provider_name=output, repository=repo_model, pull_request=pr_model)
    except ValueError as e:
        if "required" in str(e).lower() and "pr" in str(e).lower():
            print(f"❌ Error: PR number is required for {output} provider. Use --pr <number>", file=sys.stderr)
            sys.exit(1)
        raise

    try:
        has_reviewed = provider.has_reviewed()
        if has_reviewed:
            print("✅ PR has already been reviewed by the token user")
            sys.exit(0)
        else:
            print("❌ PR has not been reviewed by the token user yet")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error checking if PR has been reviewed: {e}", file=sys.stderr)
        sys.exit(1)
