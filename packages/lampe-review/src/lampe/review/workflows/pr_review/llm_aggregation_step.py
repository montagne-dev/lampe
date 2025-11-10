"""LLM-based aggregation workflow for cleaning and deduplicating review comments."""

import json
import logging
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
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, timeout=timeout, verbose=verbose, **kwargs)
        self.verbose = verbose
        self.logger = logging.getLogger(name=LAMPE_LOGGER_NAME)
        self.llm = LiteLLM(model=MODELS.GPT_5_NANO_2025_08_07, temperature=1.0, reasoning_effort="low")

    @step
    async def aggregate_reviews(self, ctx: Context, ev: LLMAggregationStartEvent) -> LLMAggregationCompleteEvent:
        """Aggregate and clean reviews using LLM."""
        if not ev.agent_reviews:
            if self.verbose:
                self.logger.debug("No agent reviews to aggregate")
            return LLMAggregationCompleteEvent(aggregated_reviews=[])

        if self.verbose:
            self.logger.debug(f"Aggregating {len(ev.agent_reviews)} agent reviews...")

        # Prepare agent reviews as JSON
        agent_reviews_dict = [review.model_dump() for review in ev.agent_reviews]
        agent_reviews_json = json.dumps(agent_reviews_dict, indent=2)

        # Create prompt
        user_prompt = LLM_AGGREGATION_USER_PROMPT.format(
            files_changed=ev.files_changed, agent_reviews_json=agent_reviews_json
        )

        # Call LLM
        response = await self.llm.achat(
            messages=[
                ChatMessage(role="system", content=LLM_AGGREGATION_SYSTEM_PROMPT),
                ChatMessage(role="user", content=user_prompt),
            ]
        )

        # Parse response
        try:
            parser = PydanticOutputParser(output_cls=AggregatedReviewsModel)
            parsed_data = parser.parse(response.message.content or "")

            # Convert back to AgentReviewOutput objects
            aggregated_reviews = []
            for agent_output_dict in parsed_data.agent_outputs:
                try:
                    aggregated_reviews.append(AgentReviewOutput.model_validate(agent_output_dict))
                except Exception as e:
                    self.logger.exception(f"Failed to parse agent output: {e}")
                    continue

            if self.verbose:
                self.logger.debug(f"Aggregation complete: {len(aggregated_reviews)} cleaned reviews")

            return LLMAggregationCompleteEvent(aggregated_reviews=aggregated_reviews)

        except Exception as e:
            self.logger.exception(f"Failed to parse aggregation response: {e}")
            # Fallback: return original reviews if aggregation fails
            if self.verbose:
                self.logger.debug("Falling back to original reviews due to aggregation failure")
            return LLMAggregationCompleteEvent(aggregated_reviews=ev.agent_reviews)
