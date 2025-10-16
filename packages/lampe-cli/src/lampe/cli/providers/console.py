from __future__ import annotations

from lampe.cli.providers.base import PRDescriptionPayload, Provider
from lampe.core.data_models.pull_request import PullRequest
from lampe.core.data_models.repository import Repository


class ConsoleProvider(Provider):
    """Console provider for delivering PR descriptions to stdout."""

    def __init__(self, repository: Repository, pull_request: PullRequest) -> None:
        super().__init__(repository, pull_request)

    def deliver_pr_description(self, payload: PRDescriptionPayload) -> None:
        """Print the PR description to console."""
        print(payload.description)
