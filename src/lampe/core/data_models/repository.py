from pydantic import BaseModel


class Repository(BaseModel):
    """Repository information."""

    local_path: str
    full_name: str | None = None
