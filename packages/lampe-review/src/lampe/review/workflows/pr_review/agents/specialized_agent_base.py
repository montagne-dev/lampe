import logging
from typing import Any

from llama_index.core.output_parsers import PydanticOutputParser
from llama_index.core.workflow import Context, StartEvent, StopEvent, step

from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.core.tools.llm_integration import git_tools_gpt_5_nano_agent_prompt
from lampe.core.workflows.function_calling_agent import (
    AgentCompleteEvent,
    FunctionCallingAgent,
    UserInputEvent,
)
from lampe.review.workflows.pr_review.agents.specialized_agent_base_prompt import (
    AGENT_PROMPT_TEMPLATE,
    BASIC_REVIEW_DEPTH_GUIDELINES,
    COMPREHENSIVE_REVIEW_DEPTH_GUIDELINES,
    STANDARD_REVIEW_DEPTH_GUIDELINES,
)
from lampe.review.workflows.pr_review.data_models import (
    AgentResponseModel,
    AgentReviewInput,
    AgentReviewOutput,
    FileReview,
    ReviewDepth,
)


class SpecializedAgentStart(StartEvent):
    """Start event for specialized review agent."""

    input: AgentReviewInput


class SpecializedAgentComplete(StopEvent):
    """Stop event for specialized review agent."""

    review_output: AgentReviewOutput


class SpecializedReviewAgent(FunctionCallingAgent):
    """Base class for specialized review agents."""

    def __init__(
        self,
        agent_name: str = "",
        focus_areas: list[str] | None = None,
        system_prompt: str = "",
        *args: Any,
        **kwargs: Any,
    ) -> None:
        # Initialize with tools that have line numbers enabled
        tools = git_tools_gpt_5_nano_agent_prompt
        super().__init__(
            *args,
            tools=tools,
            system_prompt=system_prompt,
            **kwargs,
        )
        self.agent_name = agent_name
        self.focus_areas = focus_areas or []
        self.logger = logging.getLogger(name=LAMPE_LOGGER_NAME)

    @step
    async def setup_query_and_tools(self, ctx: Context, ev: SpecializedAgentStart) -> UserInputEvent:
        """Setup the query and tools for the specialized agent."""
        review_depth_guidelines = self._get_review_depth_guidelines(ev.input.review_depth)
        query = AGENT_PROMPT_TEMPLATE.format(
            agent_name=self.agent_name,
            focus_areas=", ".join(self.focus_areas),
            pull_request_number=ev.input.pull_request.number,
            pull_request_title=ev.input.pull_request.title,
            files_changed=ev.input.files_changed,
            review_depth=ev.input.review_depth.value,
            review_depth_guidelines=review_depth_guidelines,
        )
        self.update_tools(partial_params={"repo_path": ev.input.repository.local_path, "include_line_numbers": True})
        return UserInputEvent(input=query)

    @step
    async def handle_agent_completion(self, ctx: Context, ev: AgentCompleteEvent) -> SpecializedAgentComplete:
        """Handle agent completion and generate structured output."""

        reviews = self._parse_agent_response(ev.output or "")
        result = AgentReviewOutput(
            agent_name=self.agent_name,
            focus_areas=self.focus_areas,
            reviews=reviews,
            sources=ev.sources,
            summary="",  # TODO: Add a llm generated summary of the review
        )

        return SpecializedAgentComplete(review_output=result)

    def _get_review_depth_guidelines(self, review_depth: ReviewDepth) -> str:
        """Get review depth-specific guidelines for the agent."""
        match review_depth.value:
            case "basic":
                return BASIC_REVIEW_DEPTH_GUIDELINES
            case "standard":
                return STANDARD_REVIEW_DEPTH_GUIDELINES
            case "comprehensive":
                return COMPREHENSIVE_REVIEW_DEPTH_GUIDELINES

    def _parse_agent_response(self, response_content: str) -> list[FileReview]:
        """Parse agent response into structured FileReview objects using Pydantic validation."""
        try:
            # Use the YAML Pydantic parser for robust JSON/YAML parsing
            parser = PydanticOutputParser(output_cls=AgentResponseModel)
            parsed_data = parser.parse(response_content.replace('\n"', '"'))

            reviews = []
            for review_item in parsed_data.reviews:
                file_review = FileReview(
                    file_path=review_item.get("file_path", "unknown"),
                    line_comments=review_item.get("line_comments", {}),
                    summary=review_item.get("summary", ""),
                    agent_name=self.agent_name,
                )
                reviews.append(file_review)

            return reviews
        except Exception:
            # Fallback: create a single review with the raw response
            self.logger.exception(f"Failed to parse agent response: {response_content}")
            return [
                FileReview(file_path="general", line_comments={}, summary=response_content, agent_name=self.agent_name)
            ]
