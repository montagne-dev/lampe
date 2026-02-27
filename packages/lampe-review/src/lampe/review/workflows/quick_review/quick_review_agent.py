"""Quick review agent — context-window-aware, grep-first, Claude 4.5 with extended thinking."""

import logging
from typing import Any

from llama_index.core.output_parsers import PydanticOutputParser
from llama_index.core.workflow import Context, StartEvent, step
from llama_index.llms.litellm import LiteLLM

from lampe.core.llmconfig import MODELS
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.core.tools.llm_integration import quick_review_tools
from lampe.core.workflows.function_calling_agent import (
    AgentCompleteEvent,
    FunctionCallingAgent,
    UserInputEvent,
)
from lampe.review.workflows.agentic_review.data_models import (
    ValidationAgentResponseModel,
    ValidationFinding,
    ValidationResult,
)
from lampe.review.workflows.agentic_review.validation.validation_agent import (
    ValidationAgentComplete,
)
from lampe.review.workflows.quick_review.quick_review_agent_prompt import (
    QUICK_REVIEW_AGENT_SYSTEM_PROMPT,
    QUICK_REVIEW_AGENT_USER_PROMPT,
)


class QuickReviewInput:
    """Input for quick review (no task — agent thinks about what to verify)."""

    def __init__(
        self,
        repo_path: str,
        base_commit: str,
        head_commit: str,
        files_changed: str,
    ) -> None:
        self.repo_path = repo_path
        self.base_commit = base_commit
        self.head_commit = head_commit
        self.files_changed = files_changed


class QuickReviewAgentStart(StartEvent):
    """Start event for quick review agent."""

    input: QuickReviewInput


class QuickReviewAgent(FunctionCallingAgent):
    """Lightweight review agent: grep-first, small reads, Claude 4.5 with thinking."""

    def __init__(self, llm: LiteLLM | None = None, *args: Any, **kwargs: Any) -> None:
        llm = llm or LiteLLM(
            model=MODELS.CLAUDE_4_5_SONNET_2025_09_29,
            temperature=0.3,
            reasoning_effort="medium",
        )
        super().__init__(
            *args,
            tools=quick_review_tools,
            system_prompt=QUICK_REVIEW_AGENT_SYSTEM_PROMPT,
            llm=llm,
            max_iterations=10,
            **kwargs,
        )
        self.logger = logging.getLogger(LAMPE_LOGGER_NAME)

    @step
    async def setup_query_and_tools(self, ctx: Context, ev: QuickReviewAgentStart) -> UserInputEvent:
        """Setup the quick review query and pre-fill tool params."""
        inp = ev.input
        await ctx.store.set("quick_review_input", inp)

        query = QUICK_REVIEW_AGENT_USER_PROMPT.format(
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
                "commit_reference": inp.head_commit,
                "commit_hash": inp.head_commit,
                "include_line_numbers": True,
            }
        )
        return UserInputEvent(input=query)

    @step
    async def handle_agent_completion(self, ctx: Context, ev: AgentCompleteEvent) -> ValidationAgentComplete:
        """Parse agent output into ValidationResult."""
        findings, no_issue = self._parse_response(ev.output or "", ev.sources)
        result = ValidationResult(
            task_id="quick-review",
            findings=findings,
            no_issue=no_issue,
            sources=ev.sources,
        )
        return ValidationAgentComplete(validation_result=result)

    def _parse_response(self, content: str, sources: list) -> tuple[list[ValidationFinding], bool]:
        """Parse agent response into ValidationFinding list."""
        try:
            parser = PydanticOutputParser(output_cls=ValidationAgentResponseModel)
            parsed = parser.parse(content.replace('\n"', '"'))

            findings: list[ValidationFinding] = []
            for item in parsed.findings or []:
                if isinstance(item, dict):
                    findings.append(
                        ValidationFinding(
                            file_path=str(item.get("file_path", "unknown")),
                            line_number=int(item.get("line_number", 0)),
                            action=str(item.get("action", "review")),
                            problem_summary=str(item.get("problem_summary", "")),
                            severity=str(item.get("severity", "medium")),
                            category=str(item.get("category", "general")),
                            sources=sources,
                        )
                    )

            # Quick review: only critical and high. Filter out medium/low.
            findings = [f for f in findings if f.severity in ("critical", "high")]
            no_issue = len(findings) == 0
            return findings, no_issue
        except Exception:
            self.logger.exception("Failed to parse quick review agent response")
            return [], True
