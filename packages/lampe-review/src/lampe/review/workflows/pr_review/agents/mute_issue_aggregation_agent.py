"""Agent that runs mute_issue tool calls for cleaning and deduplicating review comments."""

from typing import Any

from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from workflows import Context as WorkflowContext
from workflows import step
from workflows.events import StartEvent

from lampe.core.workflows.function_calling_agent import (
    FunctionCallingAgent,
    UserInputEvent,
)
from lampe.review.workflows.pr_review.agents.mute_issue_aggregation_agent_prompt import (
    MUTE_ISSUE_AGGREGATION_AGENT_SYSTEM_PROMPT,
)


class MuteIssueStart(StartEvent):
    """Start event for mute-issue aggregation."""

    user_prompt: str


class MuteIssueAggregationAgent(FunctionCallingAgent):
    """Agent that runs mute_issue tool calls and stores results in context."""

    @staticmethod
    def _create_mute_issue_tool() -> FunctionTool:
        async def mute_issue(ctx: Context, issue_id: str, reason: str) -> str:
            """Mark an issue as muted. Call with issue_id and a brief reason for each issue to hide."""
            muted_reasons = await ctx.store.get("muted_reasons", default=None)
            if muted_reasons is None:
                muted_reasons = {}
            muted_reasons = dict(muted_reasons)
            muted_reasons[issue_id] = reason
            await ctx.store.set("muted_reasons", muted_reasons)
            return f"Muted issue {issue_id}: {reason}"

        return FunctionTool.from_defaults(
            async_fn=mute_issue,
            name="mute_issue",
            description=(
                "Mark an issue as muted. Call with issue_id and reason for each issue to hide "
                "(e.g. duplicate, hallucination, non-actionable, noisy)."
            ),
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        tools = kwargs.pop("tools", None) or [self._create_mute_issue_tool()]
        super().__init__(
            tools=tools,
            system_prompt=kwargs.pop("system_prompt", MUTE_ISSUE_AGGREGATION_AGENT_SYSTEM_PROMPT),
            *args,
            **kwargs,
        )

    @step
    async def setup(self, ctx: WorkflowContext, ev: MuteIssueStart) -> UserInputEvent:
        """Convert input to user prompt for the agent."""
        return UserInputEvent(input=ev.user_prompt)
