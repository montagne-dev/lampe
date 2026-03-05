"""Base validation agent - task-based verification."""

import logging
from typing import Any, cast

from llama_index.core.workflow import Context, StartEvent, StopEvent, step
from llama_index.llms.litellm import LiteLLM

from lampe.core.llmconfig import MODELS, get_model
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.core.tools.llm_integration import git_tools_gpt_5_nano_agent_prompt
from lampe.core.workflows.function_calling_agent import (
    AgentCompleteEvent,
    FunctionCallingAgent,
    UserInputEvent,
)
from lampe.review.workflows.agentic_review.data_models import (
    ValidationAgentInput,
    ValidationFinding,
    ValidationResult,
)
from lampe.review.workflows.agentic_review.response_parse import parse_validation_response
from lampe.review.workflows.agentic_review.validation.validation_agent_prompt import (
    VALIDATION_AGENT_BASE_SYSTEM_PROMPT,
    VALIDATION_AGENT_USER_PROMPT,
)


class ValidationAgentStart(StartEvent):
    """Start event for validation agent."""

    input: ValidationAgentInput


class ValidationAgentComplete(StopEvent):
    """Stop event for validation agent."""

    validation_result: ValidationResult


class ValidationAgent(FunctionCallingAgent):
    """Base validation agent that executes a single verification task."""

    def __init__(self, skill_content: str = "", llm: LiteLLM | None = None, *args: Any, **kwargs: Any) -> None:
        system_prompt = VALIDATION_AGENT_BASE_SYSTEM_PROMPT

        llm = llm or LiteLLM(
            model=get_model("LAMPE_MODEL_REVIEW_VALIDATION", MODELS.GPT_5_1_CODEX_MINI),
            temperature=1.0,
            reasoning_effort="low",
        )
        if skill_content:
            from lampe.review.workflows.agentic_review.validation.validation_agent_prompt import (
                SKILL_CONTENT_SECTION,
            )

            system_prompt += SKILL_CONTENT_SECTION.format(skill_content=skill_content)

        super().__init__(
            *args,
            tools=git_tools_gpt_5_nano_agent_prompt,
            system_prompt=system_prompt,
            llm=llm,
            **kwargs,
        )
        self.logger = logging.getLogger(LAMPE_LOGGER_NAME)

    @step
    async def setup_query_and_tools(self, ctx: Context, ev: ValidationAgentStart) -> UserInputEvent:
        """Setup the validation task and tools."""
        inp = ev.input
        await ctx.store.set("validation_input", inp)

        query = VALIDATION_AGENT_USER_PROMPT.format(
            task_description=inp.task.description,
            repo_path=inp.repo_path,
            base_commit=inp.base_commit,
            head_commit=inp.head_commit,
            files_changed=inp.files_changed,
        )

        self.update_tools(
            partial_params={
                "repo_path": inp.repo_path,
                "base_reference": inp.base_commit,
                "head_reference": inp.head_commit,
                "commit_hash": inp.head_commit,
                "commit_reference": inp.head_commit,
                "include_line_numbers": True,
            }
        )
        return UserInputEvent(input=query)

    @step
    async def handle_agent_completion(self, ctx: Context, ev: AgentCompleteEvent) -> ValidationAgentComplete:
        """Parse agent output into ValidationResult."""
        # Get task_id from input - we need to stash it in context
        input_event = await ctx.store.get("validation_input")
        task_id = input_event.task.task_id if input_event else "unknown"

        findings, no_issue = self._parse_response(ev.output or "", ev.sources)
        result = ValidationResult(
            task_id=task_id,
            findings=findings,
            no_issue=no_issue,
            sources=ev.sources,
        )
        return ValidationAgentComplete(validation_result=result)

    def _parse_response(self, content: str, sources: list) -> tuple[list[ValidationFinding], bool]:
        """Parse agent response into ValidationFinding list. Gracefully handles malformed/truncated JSON."""
        parsed, success = parse_validation_response(content)
        if not success or parsed is None:
            self.logger.warning("Failed to parse validation agent response (malformed or truncated JSON)")
            return [], True

        findings: list[ValidationFinding] = []
        for item in parsed.findings or []:
            if isinstance(item, dict):
                findings.append(
                    ValidationFinding(
                        file_path=str(item.get("file_path", "unknown")),
                        line_number=int(cast(int | str, item.get("line_number", 0))),
                        action=str(item.get("action", "review")),
                        problem_summary=str(item.get("problem_summary", "")),
                        severity=str(item.get("severity", "medium")),
                        category=str(item.get("category", "general")),
                        sources=sources,
                    )
                )

        no_issue = parsed.no_issue if hasattr(parsed, "no_issue") else len(findings) == 0
        return findings, no_issue
