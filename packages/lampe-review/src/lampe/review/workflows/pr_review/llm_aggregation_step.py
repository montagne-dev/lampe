"""LLM-based aggregation workflow for cleaning and deduplicating review comments.

Uses a tool-based approach: the LLM calls mute_issue(issue_id) for each issue
to mute. Original reviews are kept with muted flags applied.
"""

import logging
from typing import Any

from llama_index.llms.litellm import LiteLLM
from workflows import Context as WorkflowContext
from workflows import Workflow, step
from workflows.events import StartEvent, StopEvent

from lampe.core.llmconfig import MODELS, get_model
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.review.workflows.pr_review.agents.mute_issue_aggregation_agent import (
    MuteIssueAggregationAgent,
    MuteIssueStart,
)
from lampe.review.workflows.pr_review.agents.mute_issue_aggregation_agent_prompt import (
    MUTE_ISSUE_AGGREGATION_USER_PROMPT,
    format_issues_as_markdown,
)
from lampe.review.workflows.pr_review.data_models import AgentReviewOutput, FileReview, ReviewComment


class LLMAggregationStartEvent(StartEvent):
    """Start event for LLM aggregation workflow."""

    agent_reviews: list[AgentReviewOutput]
    files_changed: str


class LLMAggregationCompleteEvent(StopEvent):
    """Complete event for LLM aggregation workflow."""

    aggregated_reviews: list[AgentReviewOutput]


def _build_issues_with_ids(reviews: list[AgentReviewOutput]) -> str:
    """Build a formatted string of all issues with their IDs for the LLM prompt."""
    issues: list[dict[str, Any]] = []

    for agent_idx, agent_output in enumerate(reviews):
        for file_idx, file_review in enumerate(agent_output.reviews):
            # Structured comments
            for comment_idx, comment in enumerate(file_review.structured_comments):
                issue_id = f"{agent_idx}|{file_idx}|s|{comment_idx}"
                issues.append(
                    {
                        "id": issue_id,
                        "agent": agent_output.agent_name,
                        "file": file_review.file_path,
                        "line": comment.line_number,
                        "severity": comment.severity,
                        "category": comment.category,
                        "comment": comment.comment,
                    }
                )

            # Line comments
            for line_num, comment_text in file_review.line_comments.items():
                issue_id = f"{agent_idx}|{file_idx}|l|{line_num}"
                issues.append(
                    {
                        "id": issue_id,
                        "agent": agent_output.agent_name or "unknown",
                        "file": file_review.file_path,
                        "line": line_num,
                        "severity": "n/a",
                        "category": "line_comment",
                        "comment": comment_text,
                    }
                )

    return format_issues_as_markdown(issues)


def _apply_muted_flags(reviews: list[AgentReviewOutput], muted_reasons: dict[str, str]) -> list[AgentReviewOutput]:
    """Apply muted flags and reasons to reviews based on muted issue IDs. Returns deep copies."""
    result: list[AgentReviewOutput] = []
    muted_ids = set(muted_reasons.keys())

    for agent_idx, agent_output in enumerate(reviews):
        new_reviews: list[FileReview] = []

        for file_idx, file_review in enumerate(agent_output.reviews):
            # Mark structured comments as muted
            new_structured = []
            for comment_idx, comment in enumerate(file_review.structured_comments):
                issue_id = f"{agent_idx}|{file_idx}|s|{comment_idx}"
                muted = issue_id in muted_ids
                mute_reason = muted_reasons.get(issue_id) if muted else None
                new_structured.append(
                    ReviewComment(
                        line_number=comment.line_number,
                        comment=comment.comment,
                        severity=comment.severity,
                        category=comment.category,
                        agent_name=comment.agent_name,
                        muted=muted,
                        mute_reason=mute_reason,
                    )
                )

            # Collect muted line numbers and reasons
            muted_line_numbers: set[str] = set()
            muted_line_reasons: dict[str, str] = {}
            for line_num in file_review.line_comments:
                issue_id = f"{agent_idx}|{file_idx}|l|{line_num}"
                if issue_id in muted_ids:
                    muted_line_numbers.add(line_num)
                    if issue_id in muted_reasons:
                        muted_line_reasons[line_num] = muted_reasons[issue_id]

            new_reviews.append(
                FileReview(
                    file_path=file_review.file_path,
                    line_comments=file_review.line_comments,
                    structured_comments=new_structured,
                    summary=file_review.summary,
                    agent_name=file_review.agent_name,
                    muted_line_numbers=muted_line_numbers,
                    muted_line_reasons=muted_line_reasons,
                )
            )

        result.append(
            AgentReviewOutput(
                agent_name=agent_output.agent_name,
                focus_areas=agent_output.focus_areas,
                reviews=new_reviews,
                sources=agent_output.sources,
                summary=agent_output.summary,
            )
        )

    return result


class LLMAggregationWorkflow(Workflow):
    """Workflow for aggregating and cleaning review comments using LLM tool calls.

    The LLM calls mute_issue(issue_id) for each issue to mute. Original reviews
    are preserved with muted flags applied based on tool calls.
    """

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
            model=get_model("LAMPE_MODEL_REVIEW_AGGREGATION", MODELS.GPT_5_2025_08_07),
            temperature=1,
            reasoning_effort="low",
        )
        self.max_tool_iterations = max_tool_iterations
        self._agent = MuteIssueAggregationAgent(
            llm=self.llm,
            max_iterations=self.max_tool_iterations,
            timeout=timeout,
        )

    @step
    async def aggregate_reviews(
        self, ctx: WorkflowContext, ev: LLMAggregationStartEvent
    ) -> LLMAggregationCompleteEvent:
        """Aggregate and clean reviews using LLM with mute_issue tool calls."""
        if not ev.agent_reviews:
            if self.verbose:
                self.logger.debug("No agent reviews to aggregate")
            return LLMAggregationCompleteEvent(aggregated_reviews=[])

        if self.verbose:
            self.logger.debug(f"Aggregating {len(ev.agent_reviews)} agent reviews via mute_issue tool...")

        issues_with_ids = _build_issues_with_ids(ev.agent_reviews)
        user_prompt = MUTE_ISSUE_AGGREGATION_USER_PROMPT.format(
            files_changed=ev.files_changed, issues_with_ids=issues_with_ids
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
            aggregated_reviews = _apply_muted_flags(ev.agent_reviews, muted_reasons)

            if self.verbose:
                self.logger.debug(f"Aggregation complete: muted {len(muted_reasons)} issues")

        except Exception as e:
            self.logger.exception(f"Failed to aggregate reviews: {e}")
            if self.verbose:
                self.logger.debug("Falling back to original reviews")
            aggregated_reviews = ev.agent_reviews

        if self.verbose:
            self.logger.debug(f"Aggregation complete: {len(aggregated_reviews)} reviews with muted flags")

        return LLMAggregationCompleteEvent(aggregated_reviews=aggregated_reviews)
