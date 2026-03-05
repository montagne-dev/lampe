"""Hallucination filter step — uses cheap LLM with mute_issue tool to remove investigation-request comments."""

import logging
from typing import Any

from llama_index.llms.litellm import LiteLLM
from workflows import Context as WorkflowContext
from workflows import Workflow, step
from workflows.events import StartEvent, StopEvent

from lampe.core.llmconfig import MODELS
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.review.workflows.pr_review.agents.mute_issue_aggregation_agent import (
    MuteIssueAggregationAgent,
    MuteIssueStart,
)
from lampe.review.workflows.pr_review.data_models import AgentReviewOutput
from lampe.review.workflows.pr_review.llm_aggregation_step import (
    _apply_muted_flags,
    _build_issues_with_ids,
)
from lampe.review.workflows.quick_review.hallucination_filter_prompt import (
    HALLUCINATION_FILTER_SYSTEM_PROMPT,
    HALLUCINATION_FILTER_USER_PROMPT,
)


class HallucinationFilterStartEvent(StartEvent):
    """Start event for hallucination filter."""

    agent_reviews: list[AgentReviewOutput]
    files_changed: str


class HallucinationFilterCompleteEvent(StopEvent):
    """Complete event for hallucination filter."""

    filtered_reviews: list[AgentReviewOutput]


class HallucinationFilterWorkflow(Workflow):
    """Workflow to mute investigation-request comments using a cheap LLM and mute_issue tool."""

    def __init__(
        self,
        timeout: int | None = None,
        verbose: bool = False,
        max_tool_iterations: int = 5,
        llm: Any | None = None,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, timeout=timeout, verbose=verbose, **kwargs)
        self.verbose = verbose
        self.logger = logging.getLogger(name=LAMPE_LOGGER_NAME)
        self.llm = llm or LiteLLM(
            model=MODELS.GPT_5_NANO_2025_08_07,
            temperature=0.2,
        )
        self.max_tool_iterations = max_tool_iterations
        self._agent = MuteIssueAggregationAgent(
            llm=self.llm,
            max_iterations=self.max_tool_iterations,
            timeout=timeout,
            system_prompt=HALLUCINATION_FILTER_SYSTEM_PROMPT,
        )

    @step
    async def filter_hallucinations(
        self, ctx: WorkflowContext, ev: HallucinationFilterStartEvent
    ) -> HallucinationFilterCompleteEvent:
        """Run hallucination filter: mute comments that ask reader to investigate."""
        if not ev.agent_reviews:
            return HallucinationFilterCompleteEvent(filtered_reviews=[])

        # Skip if no findings to filter
        issues_with_ids = _build_issues_with_ids(ev.agent_reviews)
        if "_No issues to review._" in issues_with_ids:
            return HallucinationFilterCompleteEvent(filtered_reviews=ev.agent_reviews)

        if self.verbose:
            self.logger.debug("Running hallucination filter via mute_issue tool...")

        user_prompt = HALLUCINATION_FILTER_USER_PROMPT.format(
            files_changed=ev.files_changed,
            issues_with_ids=issues_with_ids,
        )

        try:
            agent_ctx = WorkflowContext(self._agent)
            await agent_ctx.store.set("muted_reasons", {})
            await self._agent.run(
                start_event=MuteIssueStart(user_prompt=user_prompt),
                ctx=agent_ctx,
            )
            muted_reasons = await agent_ctx.store.get("muted_reasons", default={})
            muted_reasons = dict(muted_reasons) if muted_reasons else {}
            filtered_reviews = _apply_muted_flags(ev.agent_reviews, muted_reasons)

            if self.verbose and muted_reasons:
                self.logger.debug(f"Hallucination filter muted {len(muted_reasons)} issues")

        except Exception as e:
            self.logger.exception(f"Hallucination filter failed: {e}")
            filtered_reviews = ev.agent_reviews

        return HallucinationFilterCompleteEvent(filtered_reviews=filtered_reviews)
