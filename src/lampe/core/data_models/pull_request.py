from pydantic import BaseModel


class PullRequest(BaseModel):
    """Pull request information."""

    number: int
    title: str
    body: str | None = None
    base_commit_hash: str
    base_branch_name: str
    head_commit_hash: str
    head_branch_name: str
