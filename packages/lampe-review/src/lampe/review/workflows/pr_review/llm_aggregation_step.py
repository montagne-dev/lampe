"""LLM-based aggregation workflow for cleaning and deduplicating review comments."""

import json
import logging
import random
from typing import Any

from llama_index.core.llms import ChatMessage
from llama_index.core.output_parsers import PydanticOutputParser
from llama_index.core.workflow import Context, StartEvent, StopEvent
from llama_index.llms.litellm import LiteLLM
from pydantic import BaseModel, Field
from workflows import Workflow, step

from lampe.core.llmconfig import MODELS
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.review.workflows.pr_review.data_models import AgentReviewOutput
from lampe.review.workflows.pr_review.llm_aggregation_prompt import (
    LLM_AGGREGATION_SYSTEM_PROMPT,
    LLM_AGGREGATION_USER_PROMPT,
)


class AggregatedReviewsModel(BaseModel):
    """Pydantic model for LLM aggregation output."""

    agent_outputs: list[dict[str, Any]] = Field(..., description="List of cleaned agent review outputs")


class LLMAggregationStartEvent(StartEvent):
    """Start event for LLM aggregation workflow."""

    agent_reviews: list[AgentReviewOutput]
    files_changed: str


class LLMAggregationCompleteEvent(StopEvent):
    """Complete event for LLM aggregation workflow."""

    aggregated_reviews: list[AgentReviewOutput]


class LLMAggregationWorkflow(Workflow):
    """Workflow for aggregating and cleaning review comments using LLM."""

    def __init__(
        self,
        timeout: int | None = None,
        verbose: bool = False,
        max_batch_size: int = 10,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, timeout=timeout, verbose=verbose, **kwargs)
        self.verbose = verbose
        self.logger = logging.getLogger(name=LAMPE_LOGGER_NAME)
        self.llm = LiteLLM(model=MODELS.GPT_5_2025_08_07, temperature=1, reasoning_effort="high")
        self.max_batch_size = max_batch_size

    def _group_reviews_by_directory(self, reviews: list[AgentReviewOutput]) -> list[list[AgentReviewOutput]]:
        """Group agent reviews by first folder in file paths."""
        groups: dict[str, list[AgentReviewOutput]] = {}
        ungrouped: list[AgentReviewOutput] = []

        for review in reviews:
            # Extract first folder from file paths in reviews
            first_folders = set()
            for file_review in review.reviews:
                file_path = file_review.file_path
                # Extract first folder (e.g., "src/utils/helper.py" -> "src")
                parts = file_path.split("/", 1)
                if len(parts) > 1:
                    first_folders.add(parts[0])
                elif file_path.startswith("/"):
                    # Handle absolute paths
                    parts = file_path.lstrip("/").split("/", 1)
                    if len(parts) > 1:
                        first_folders.add(parts[0])

            # Try to find a matching group
            matched = False
            for folder in first_folders:
                if folder in groups:
                    groups[folder].append(review)
                    matched = True
                    break

            if not matched:
                # If no match found, add to ungrouped or create new group
                if first_folders:
                    # Use the first folder found
                    folder = next(iter(first_folders))
                    groups[folder] = [review]
                else:
                    # No folder structure, add to ungrouped
                    ungrouped.append(review)

        # Distribute ungrouped reviews randomly to existing groups
        result = list(groups.values())
        if ungrouped:
            if result:
                # Distribute ungrouped reviews to existing groups
                for review in ungrouped:
                    random_group = random.choice(result)
                    random_group.append(review)
            else:
                # No groups exist, create one with ungrouped reviews
                result = [ungrouped]

        return result

    @step
    async def aggregate_reviews(self, ctx: Context, ev: LLMAggregationStartEvent) -> LLMAggregationCompleteEvent:
        """Aggregate and clean reviews using LLM with batched processing."""
        if not ev.agent_reviews:
            if self.verbose:
                self.logger.debug("No agent reviews to aggregate")
            return LLMAggregationCompleteEvent(aggregated_reviews=[])

        if self.verbose:
            self.logger.debug(f"Aggregating {len(ev.agent_reviews)} agent reviews...")

        # Group reviews by directory structure
        grouped_reviews = self._group_reviews_by_directory(ev.agent_reviews)

        if self.verbose:
            self.logger.debug(f"Grouped reviews into {len(grouped_reviews)} directory-based groups")

        # Process reviews in batches
        all_batches: list[list[AgentReviewOutput]] = []
        for group in grouped_reviews:
            # Split large groups into smaller batches
            for i in range(0, len(group), self.max_batch_size):
                batch = group[i : i + self.max_batch_size]
                all_batches.append(batch)

        if self.verbose:
            self.logger.debug(f"Processing {len(all_batches)} batches (max {self.max_batch_size} reviews per batch)")

        # Process each batch
        aggregated_reviews: list[AgentReviewOutput] = []
        for batch_idx, batch in enumerate(all_batches):
            if self.verbose:
                self.logger.debug(f"Processing batch {batch_idx + 1}/{len(all_batches)} with {len(batch)} reviews")

            # Convert to lightweight version (strip tool_output from sources)
            agent_reviews_dict = [review.to_lightweight_dict() for review in batch]
            agent_reviews_json = json.dumps(agent_reviews_dict, indent=2)

            # Create prompt
            user_prompt = LLM_AGGREGATION_USER_PROMPT.format(
                files_changed=ev.files_changed, agent_reviews_json=agent_reviews_json
            )

            # Call LLM
            try:
                response = await self.llm.achat(
                    messages=[
                        ChatMessage(role="system", content=LLM_AGGREGATION_SYSTEM_PROMPT),
                        ChatMessage(role="user", content=user_prompt),
                    ]
                )

                # Parse response
                parser = PydanticOutputParser(output_cls=AggregatedReviewsModel)
                parsed_data = parser.parse(response.message.content or "")

                # Convert back to AgentReviewOutput objects
                for agent_output_dict in parsed_data.agent_outputs:
                    try:
                        aggregated_reviews.append(AgentReviewOutput.model_validate(agent_output_dict))
                    except Exception as e:
                        self.logger.exception(f"Failed to parse agent output in batch {batch_idx + 1}: {e}")
                        continue

            except Exception as e:
                self.logger.exception(f"Failed to aggregate batch {batch_idx + 1}: {e}")
                # Fallback: add original reviews from this batch
                if self.verbose:
                    self.logger.debug(f"Falling back to original reviews for batch {batch_idx + 1}")
                aggregated_reviews.extend(batch)

        if self.verbose:
            self.logger.debug(f"Aggregation complete: {len(aggregated_reviews)} cleaned reviews")

        return LLMAggregationCompleteEvent(aggregated_reviews=aggregated_reviews)
