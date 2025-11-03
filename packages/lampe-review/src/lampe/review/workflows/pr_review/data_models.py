from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from lampe.core.data_models import PullRequest, Repository


class AgentResponseModel(BaseModel):
    """Pydantic model for agent JSON response parsing."""

    reviews: List[Dict[str, Any]] = Field(..., description="List of file reviews")
    summary: str = Field(..., description="Overall summary from the agent")


class ReviewDepth(str, Enum):
    """Review depth levels for PR reviews."""

    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"


class ReviewComment(BaseModel):
    """Structured comment with metadata."""

    line_number: int = Field(..., description="Line number where the comment applies")
    comment: str = Field(..., description="The review comment text")
    severity: str = Field(..., description="Severity level: critical, high, medium, low")
    category: str = Field(..., description="Category of the issue (e.g., security, performance, quality)")
    agent_name: str = Field(..., description="Name of the agent that found this issue")


class FileReview(BaseModel):
    """Review for a specific file with inline comments."""

    file_path: str = Field(..., description="Path to the reviewed file")
    line_comments: Dict[int, str] = Field(default_factory=dict, description="Line number to comment mapping")
    structured_comments: List[ReviewComment] = Field(
        default_factory=list, description="Structured comments with metadata"
    )
    summary: str = Field(..., description="Overall summary of the file review")
    agent_name: Optional[str] = Field(default=None, description="Name of the agent that performed this review")


class AgentReviewInput(BaseModel):
    """Input for individual specialized agents."""

    repository: Repository
    pull_request: PullRequest
    files_changed: str = Field(..., description="Formatted string of changed files with stats")
    review_depth: ReviewDepth = Field(default=ReviewDepth.STANDARD, description="Depth of review analysis")
    custom_guidelines: Optional[List[str]] = Field(default=None, description="Custom review guidelines to focus on")


class AgentReviewOutput(BaseModel):
    """Output from individual specialized agents."""

    agent_name: str = Field(..., description="Name of the agent that performed the review")
    focus_areas: List[str] = Field(..., description="Areas this agent focuses on")
    reviews: List[FileReview] = Field(default_factory=list, description="File reviews from this agent")
    summary: str = Field(..., description="Overall summary from this agent")


class PRReviewInput(BaseModel):
    """Input for PR review generation workflow."""

    repository: Repository
    pull_request: PullRequest
    review_depth: ReviewDepth = Field(default=ReviewDepth.STANDARD, description="Depth of review analysis")
    custom_guidelines: Optional[List[str]] = Field(default=None, description="Custom review guidelines to focus on")
    files_exclude_patterns: Optional[List[str]] = Field(
        default=None, description="File patterns to exclude from review"
    )
    files_include_patterns: Optional[List[str]] = Field(default=None, description="File patterns to include in review")
    files_reinclude_patterns: Optional[List[str]] = Field(
        default=None, description="File patterns to reinclude after exclusion"
    )
    use_multi_agent: bool = Field(default=True, description="Whether to use multi-agent pipeline or single agent")


class PRReviewOutput(BaseModel):
    """Output model for PR review generation."""

    reviews: list[FileReview] = Field(..., description="List of file reviews with inline comments")
