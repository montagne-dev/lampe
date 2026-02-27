"""Data models for the agentic review workflow."""

from pydantic import BaseModel, Field

from lampe.core.workflows.function_calling_agent import ToolSource


class PRIntent(BaseModel):
    """Extracted intent from the PR."""

    summary: str = Field(
        default="",
        description="Brief summary of what the PR does",
    )
    areas_touched: list[str] = Field(
        default_factory=list,
        description="Areas touched: e.g. data, api, tests, security",
    )
    suggested_validation_tasks: list[str] = Field(
        default_factory=list,
        description="Concrete validation tasks the orchestrator should run",
    )


class ValidationTask(BaseModel):
    """Single task to send to a Validation Agent."""

    task_id: str = Field(..., description="Unique identifier for the task")
    description: str = Field(..., description="Concrete validation question for the agent")
    applicable_skill_paths: list[str] = Field(
        default_factory=list,
        description="Paths to SKILL.md content that applies",
    )
    skill_content: str = Field(
        default="",
        description="Resolved SKILL.md content to inject into prompt (empty for basic agent)",
    )


class TaskPlanningOutput(BaseModel):
    """Structured output from task planning."""

    tasks: list[ValidationTask] = Field(
        default_factory=list,
        description="List of basic validation tasks (orchestrator-formulated)",
    )
    # Second field avoids llama_index call_tool bug: with 1 prop + 1 arg it unwraps
    # to tool(value) instead of tool(**kwargs), causing model_fn to receive empty kwargs
    note: str = Field(default="", description="Optional brief note. Can be empty.")


class ValidationAgentInput(BaseModel):
    """Input for the validation agent."""

    task: ValidationTask = Field(..., description="The validation task to execute")
    repo_path: str = Field(..., description="Path to the repository")
    base_commit: str = Field(..., description="Base commit reference")
    head_commit: str = Field(..., description="Head commit reference")
    files_changed: str = Field(..., description="Formatted list of changed files")


class ValidationFinding(BaseModel):
    """Structured finding from a validation agent."""

    file_path: str = Field(..., description="Path to the file with the issue")
    line_number: int = Field(..., description="Line number where the issue occurs")
    action: str = Field(..., description="Suggested action: fix, review, consider")
    problem_summary: str = Field(..., description="Summary of the problem found")
    severity: str = Field(..., description="Severity: critical, high, medium, low")
    category: str = Field(..., description="Category: security, data, api, etc.")
    sources: list[ToolSource] = Field(
        default_factory=list,
        description="Tools used to find this issue (populated from agent run)",
    )


class ValidationAgentResponseModel(BaseModel):
    """Pydantic model for validation agent JSON response parsing."""

    no_issue: bool = Field(default=True, description="True if no problems found")
    findings: list[dict[str, object]] = Field(
        default_factory=list,
        description="Structured findings when problems exist",
    )


class ValidationResult(BaseModel):
    """Output from a Validation Agent."""

    task_id: str = Field(..., description="ID of the task that was executed")
    findings: list[ValidationFinding] = Field(
        default_factory=list,
        description="Structured findings when problems exist",
    )
    no_issue: bool = Field(
        default=True,
        description="True if agent found nothing wrong",
    )
    sources: list[ToolSource] = Field(
        default_factory=list,
        description="All tool sources from the agent run",
    )
