from pydantic import BaseModel


class Issue(BaseModel):
    """Individual issue to be resolved."""

    guid: str
    description: str
    commit_hash: str
    line_start: int
    line_end: int
    file_path: str
