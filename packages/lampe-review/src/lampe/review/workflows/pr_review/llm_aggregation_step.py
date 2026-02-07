"""LLM-based aggregation workflow for cleaning and deduplicating review comments.

Uses a tool-based approach: the LLM calls mute_issue(issue_id) for each issue
to mute. Original reviews are kept with muted flags applied.
"""

import json
import logging
import random
from typing import Any

from llama_index.core.llms import ChatMessage
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools import FunctionTool
from llama_index.llms.litellm import LiteLLM
from workflows import Context, Workflow, step
from workflows.events import StartEvent, StopEvent

from lampe.core.llmconfig import MODELS
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.review.workflows.pr_review.data_models import AgentReviewOutput, FileReview, ReviewComment
from lampe.review.workflows.pr_review.llm_aggregation_prompt import (
    LLM_AGGREGATION_SYSTEM_PROMPT,
    LLM_AGGREGATION_USER_PROMPT,
)


class LLMAggregationStartEvent(StartEvent):
    """Start event for LLM aggregation workflow."""

    agent_reviews: list[AgentReviewOutput]
    files_changed: str


class LLMAggregationCompleteEvent(StopEvent):
    """Complete event for LLM aggregation workflow."""

    aggregated_reviews: list[AgentReviewOutput]


def _build_issues_with_ids(batch: list[AgentReviewOutput]) -> str:
    """Build a formatted string of all issues with their IDs for the LLM prompt."""
    issues: list[dict[str, Any]] = []

    for agent_idx, agent_output in enumerate(batch):
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
                        "comment": comment.comment[:200] + ("..." if len(comment.comment) > 200 else ""),
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
                        "comment": (comment_text[:200] + "...") if len(comment_text) > 200 else comment_text,
                    }
                )

    return json.dumps(issues, indent=2)


def _apply_muted_flags(
    batch: list[AgentReviewOutput], muted_ids: set[str]
) -> list[AgentReviewOutput]:
    """Apply muted flags to reviews based on muted issue IDs. Returns deep copies."""
    result: list[AgentReviewOutput] = []

    for agent_idx, agent_output in enumerate(batch):
        new_reviews: list[FileReview] = []

        for file_idx, file_review in enumerate(agent_output.reviews):
            # Mark structured comments as muted
            new_structured = []
            for comment_idx, comment in enumerate(file_review.structured_comments):
                issue_id = f"{agent_idx}|{file_idx}|s|{comment_idx}"
                muted = issue_id in muted_ids
                new_structured.append(
                    ReviewComment(
                        line_number=comment.line_number,
                        comment=comment.comment,
                        severity=comment.severity,
                        category=comment.category,
                        agent_name=comment.agent_name,
                        muted=muted,
                    )
                )

            # Collect muted line numbers
            muted_line_numbers: set[str] = set()
            for line_num in file_review.line_comments:
                issue_id = f"{agent_idx}|{file_idx}|l|{line_num}"
                if issue_id in muted_ids:
                    muted_line_numbers.add(line_num)

            new_reviews.append(
                FileReview(
                    file_path=file_review.file_path,
                    line_comments=file_review.line_comments,
                    structured_comments=new_structured,
                    summary=file_review.summary,
                    agent_name=file_review.agent_name,
                    muted_line_numbers=muted_line_numbers,
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
        max_batch_size: int = 10,
        max_tool_iterations: int = 5,
        llm: Any | None = None,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, timeout=timeout, verbose=verbose, **kwargs)
        self.verbose = verbose
        self.logger = logging.getLogger(name=LAMPE_LOGGER_NAME)
        self.llm = llm or LiteLLM(model=MODELS.GPT_5_2025_08_07, temperature=1, reasoning_effort='high')
        self.max_batch_size = max_batch_size
        self.max_tool_iterations = max_tool_iterations

    def _group_reviews_by_directory(self, reviews: list[AgentReviewOutput]) -> list[list[AgentReviewOutput]]:
        """Group agent reviews by first folder in file paths."""
        groups: dict[str, list[AgentReviewOutput]] = {}
        ungrouped: list[AgentReviewOutput] = []

        for review in reviews:
            first_folders = set()
            for file_review in review.reviews:
                file_path = file_review.file_path
                parts = file_path.split('/', 1)
                if len(parts) > 1:
                    first_folders.add(parts[0])
                elif file_path.startswith('/'):
                    parts = file_path.lstrip('/').split('/', 1)
                    if len(parts) > 1:
                        first_folders.add(parts[0])

            matched = False
            for folder in first_folders:
                if folder in groups:
                    groups[folder].append(review)
                    matched = True
                    break

            if not matched:
                if first_folders:
                    folder = next(iter(first_folders))
                    groups[folder] = [review]
                else:
                    ungrouped.append(review)

        result = list(groups.values())
        if ungrouped:
            if result:
                for review in ungrouped:
                    random_group = random.choice(result)
                    random_group.append(review)
            else:
                result = [ungrouped]

        return result

    @step
    async def aggregate_reviews(self, ctx: Context, ev: LLMAggregationStartEvent) -> LLMAggregationCompleteEvent:
        """Aggregate and clean reviews using LLM with mute_issue tool calls."""
        if not ev.agent_reviews:
            if self.verbose:
                self.logger.debug('No agent reviews to aggregate')
            return LLMAggregationCompleteEvent(aggregated_reviews=[])

        if self.verbose:
            self.logger.debug(f'Aggregating {len(ev.agent_reviews)} agent reviews via mute_issue tool...')

        grouped_reviews = self._group_reviews_by_directory(ev.agent_reviews)

        all_batches: list[list[AgentReviewOutput]] = []
        for group in grouped_reviews:
            for i in range(0, len(group), self.max_batch_size):
                batch = group[i : i + self.max_batch_size]
                all_batches.append(batch)

        if self.verbose:
            self.logger.debug(f'Processing {len(all_batches)} batches (max {self.max_batch_size} reviews per batch)')

        aggregated_reviews: list[AgentReviewOutput] = []
        for batch_idx, batch in enumerate(all_batches):
            if self.verbose:
                self.logger.debug(f'Processing batch {batch_idx + 1}/{len(all_batches)} with {len(batch)} reviews')

            muted_ids: set[str] = set()

            def mute_issue(issue_id: str) -> str:
                """Mark an issue as muted. Call this for each issue you want to hide from the final review."""
                return f'Muted issue {issue_id}'

            tool = FunctionTool.from_defaults(
                fn=mute_issue,
                name='mute_issue',
                description=(
                    'Mark an issue as muted. Call with issue_id for each issue to hide '
                    '(duplicates, hallucinations, non-actionable, noisy).'
                ),
            )

            issues_with_ids = _build_issues_with_ids(batch)
            user_prompt = LLM_AGGREGATION_USER_PROMPT.format(
                files_changed=ev.files_changed, issues_with_ids=issues_with_ids
            )

            memory = ChatMemoryBuffer.from_defaults(llm=self.llm)
            memory.put(ChatMessage(role='system', content=LLM_AGGREGATION_SYSTEM_PROMPT))
            memory.put(ChatMessage(role='user', content=user_prompt))

            try:
                iteration = 0
                while iteration < self.max_tool_iterations:
                    iteration += 1
                    chat_history = memory.get()
                    response = await self.llm.achat_with_tools([tool], chat_history=chat_history)

                    memory.put(response.message)
                    tool_calls = self.llm.get_tool_calls_from_response(response, error_on_no_tool_call=False)

                    if not tool_calls:
                        break

                    for tool_call in tool_calls:
                        if tool_call.tool_name == 'mute_issue':
                            issue_id = tool_call.tool_kwargs.get('issue_id', '')
                            if issue_id:
                                muted_ids.add(issue_id)
                        memory.put(
                            ChatMessage(
                                role='tool',
                                content='Muted',
                                additional_kwargs={'tool_call_id': tool_call.tool_id, 'name': tool_call.tool_name},
                            )
                        )

                batch_with_muted = _apply_muted_flags(batch, muted_ids)
                aggregated_reviews.extend(batch_with_muted)

                if self.verbose:
                    self.logger.debug(f'Batch {batch_idx + 1}: muted {len(muted_ids)} issues')

            except Exception as e:
                self.logger.exception(f'Failed to aggregate batch {batch_idx + 1}: {e}')
                if self.verbose:
                    self.logger.debug(f'Falling back to original reviews for batch {batch_idx + 1}')
                aggregated_reviews.extend(batch)

        if self.verbose:
            self.logger.debug(f'Aggregation complete: {len(aggregated_reviews)} reviews with muted flags')

        return LLMAggregationCompleteEvent(aggregated_reviews=aggregated_reviews)
