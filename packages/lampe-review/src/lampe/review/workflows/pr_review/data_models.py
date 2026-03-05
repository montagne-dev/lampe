from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_serializer

from lampe.core.data_models import PullRequest, Repository
from lampe.core.workflows.function_calling_agent import ToolSource

ISSUE_BLOCK_TEMPLATE = """### Issue `{issue_id}`
- **Agent:** {agent}
- **File:** `{file}`
- **Line:** {line}
- **Severity:** {severity}
- **Category:** {category}
- **Comment:** {comment}
"""


class LightweightToolSource(BaseModel):
    """Lightweight version of ToolSource without tool_output for aggregation."""

    tool_name: str = Field(..., description="Name of the tool that was called")
    tool_kwargs: dict[str, Any] = Field(..., description="Arguments passed to the tool")


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
    muted: bool = Field(default=False, description="Whether this issue was muted during aggregation")
    mute_reason: Optional[str] = Field(
        default=None, description="Reason why this issue was muted (e.g. duplicate, hallucination)"
    )


class FileReview(BaseModel):
    """Review for a specific file with inline comments."""

    file_path: str = Field(..., description="Path to the reviewed file")
    line_comments: dict[str, str] = Field(default_factory=dict, description="Line number to comment mapping")
    structured_comments: list[ReviewComment] = Field(
        default_factory=list, description="Structured comments with metadata"
    )
    summary: str = Field(..., description="Overall summary of the file review")
    agent_name: Optional[str] = Field(default=None, description="Name of the agent that performed this review")
    muted_line_numbers: set[str] = Field(
        default_factory=set, description="Line numbers with muted comments (for line_comments)"
    )
    muted_line_reasons: dict[str, str] = Field(
        default_factory=dict, description="Line number to mute reason (for line_comments)"
    )

    @field_serializer("muted_line_numbers")
    def _serialize_muted_line_numbers(self, value: set[str]) -> list[str]:
        """Serialize set to sorted list for JSON compatibility."""
        return sorted(value)


class IssueWithId(BaseModel):
    """Single issue with its mute ID, for use in aggregator/hallucination prompts."""

    issue_id: str = Field(..., description="ID for mute_issue tool (agent_idx|file_idx|s|l|key)")
    agent: str = Field(..., description="Agent that produced the comment")
    file: str = Field(..., description="File path")
    line: str | int = Field(..., description="Line number")
    severity: str = Field(..., description="Severity level")
    category: str = Field(..., description="Category of the issue")
    comment: str = Field(..., description="Comment text")

    def to_markdown_block(self) -> str:
        """Format this issue as a markdown block for LLM prompts."""
        return ISSUE_BLOCK_TEMPLATE.format(
            issue_id=self.issue_id,
            agent=self.agent,
            file=self.file,
            line=self.line,
            severity=self.severity,
            category=self.category,
            comment=self.comment,
        ).strip()

    @classmethod
    def build_from_agent_reviews(cls, reviews: list["AgentReviewOutput"]) -> list["IssueWithId"]:
        """Build IssueWithId list from agent reviews. Reusable for aggregator and hallucination filter."""
        issues: list[IssueWithId] = []
        for agent_idx, agent_output in enumerate(reviews):
            for file_idx, file_review in enumerate(agent_output.reviews):
                for comment_idx, rc in enumerate(file_review.structured_comments):
                    issues.append(
                        cls(
                            issue_id=f"{agent_idx}|{file_idx}|s|{comment_idx}",
                            agent=agent_output.agent_name,
                            file=file_review.file_path,
                            line=rc.line_number,
                            severity=rc.severity,
                            category=rc.category,
                            comment=rc.comment,
                        )
                    )
                for line_num, comment_text in file_review.line_comments.items():
                    issues.append(
                        cls(
                            issue_id=f"{agent_idx}|{file_idx}|l|{line_num}",
                            agent=agent_output.agent_name or "unknown",
                            file=file_review.file_path,
                            line=line_num,
                            severity="n/a",
                            category="line_comment",
                            comment=comment_text,
                        )
                    )
        return issues

    @staticmethod
    def format_list_for_prompt(issues: list["IssueWithId"]) -> str:
        """Format a list of issues as markdown for the LLM prompt."""
        if not issues:
            return "_No issues to review._"
        return "\n\n".join(issue.to_markdown_block() for issue in issues)


class AgentReviewOutput(BaseModel):
    """Output from individual specialized agents."""

    agent_name: str = Field(..., description="Name of the agent that performed the review")
    focus_areas: list[str] = Field(..., description="Areas this agent focuses on")
    reviews: list[FileReview] = Field(default_factory=list, description="File reviews from this agent")
    sources: list[ToolSource] = Field(default_factory=list, description="Sources from this agent")
    summary: str = Field(..., description="Overall summary from this agent")

    def to_lightweight_dict(self) -> dict[str, Any]:
        """Convert to dictionary with lightweight sources for aggregation."""
        lightweight_sources = [
            LightweightToolSource(tool_name=source.tool_name, tool_kwargs=source.tool_kwargs).model_dump()
            for source in self.sources
        ]
        return {
            "agent_name": self.agent_name,
            "focus_areas": self.focus_areas,
            "reviews": [review.model_dump() for review in self.reviews],
            "sources": lightweight_sources,
            "summary": self.summary,
        }


class PRReviewInput(BaseModel):
    """Input for PR review generation workflow."""

    repository: Repository
    pull_request: PullRequest
    review_depth: ReviewDepth = Field(default=ReviewDepth.STANDARD, description="Depth of review analysis")
    custom_guidelines: Optional[list[str]] = Field(default=None, description="Custom review guidelines to focus on")
    files_exclude_patterns: Optional[list[str]] = Field(
        default=None, description="File patterns to exclude from review"
    )
    files_include_patterns: Optional[list[str]] = Field(default=None, description="File patterns to include in review")
    files_reinclude_patterns: Optional[list[str]] = Field(
        default=None, description="File patterns to reinclude after exclusion"
    )


class PRReivewAggregatorOutput(BaseModel):
    """Output model for PR review aggregation."""

    reviews: list[FileReview] = Field(..., description="List of file reviews")
