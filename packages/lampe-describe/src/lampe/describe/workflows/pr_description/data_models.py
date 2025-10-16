from pydantic import BaseModel

from lampe.core.data_models import PullRequest, Repository


class PRDescriptionInput(BaseModel):
    """Input for PR description generation workflow."""

    repository: Repository
    pull_request: PullRequest
    files_exclude_patterns: list[str] | None = None
    files_include_patterns: list[str] | None = None
    files_reinclude_patterns: list[str] | None = None
