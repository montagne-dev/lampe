import logging
from typing import Any, List

from llama_index.core.workflow import Context, StartEvent, StopEvent, step

from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.core.parsers.yaml_pydantic_output import YAMLPydanticOutputParser
from lampe.core.tools.llm_integration import git_tools_gpt_5_nano_agent_prompt
from lampe.core.workflows.function_calling_agent import (
    AgentCompleteEvent,
    FunctionCallingAgent,
    InputEvent,
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

    input: str


class SpecializedAgentComplete(StopEvent):
    """Stop event for specialized review agent."""

    review_output: AgentReviewOutput


class SpecializedReviewAgent(FunctionCallingAgent):
    """Base class for specialized review agents."""

    def __init__(self, agent_name: str, focus_areas: List[str], system_prompt: str, *args: Any, **kwargs: Any) -> None:
        # Initialize with tools that have line numbers enabled
        tools = git_tools_gpt_5_nano_agent_prompt
        super().__init__(
            *args,
            tools=tools,
            system_prompt=system_prompt,
            **kwargs,
        )
        self.agent_name = agent_name
        self.focus_areas = focus_areas
        self.logger = logging.getLogger(name=LAMPE_LOGGER_NAME)

    def update_tools(self, partial_params: dict[str, Any] | None = None) -> None:
        """Update tool parameters, enabling line numbers for specialized agents."""
        for tool in self.tools:
            if hasattr(tool, "partial_params"):
                if partial_params is not None:
                    # Enable line numbers for specialized agents
                    tool.partial_params = {**partial_params, "include_line_numbers": True}
                else:
                    tool.partial_params = {"include_line_numbers": True}

    @step
    async def prepare_chat_history(self, ctx: Context, ev: SpecializedAgentStart) -> InputEvent:
        """Override the start event to handle specialized agent logic."""
        # Store the input for later use
        await ctx.store.set("agent_input", ev.input)

        # Call the parent's prepare_chat_history method
        return await super().prepare_chat_history(ctx, ev)

    @step
    async def handle_agent_completion(self, ctx: Context, ev: AgentCompleteEvent) -> SpecializedAgentComplete:
        """Handle agent completion and generate structured output."""
        # Get the stored agent input
        agent_input = await ctx.store.get("full_agent_input")

        if not agent_input:
            # Fallback: create a basic review output
            reviews = self._parse_agent_response(ev.output or "")
            result = AgentReviewOutput(
                agent_name=self.agent_name,
                focus_areas=self.focus_areas,
                reviews=reviews,
                summary=self._extract_summary(ev.output or ""),
            )
        else:
            # Parse the response and create structured output
            reviews = self._parse_agent_response(ev.output or "")
            result = AgentReviewOutput(
                agent_name=self.agent_name,
                focus_areas=self.focus_areas,
                reviews=reviews,
                summary=self._extract_summary(ev.output or ""),
            )

        return SpecializedAgentComplete(review_output=result)

    async def review(self, input: AgentReviewInput) -> AgentReviewOutput:
        """Perform specialized review focusing on agent's expertise areas."""
        # Create agent-specific prompt
        query = self._create_agent_prompt(input)

        # Update tools with repository path and line numbers enabled
        self.update_tools(partial_params={"repo_path": input.repository.local_path})

        # Store the full input for the workflow
        ctx = Context(self)
        await ctx.store.set("full_agent_input", input)

        # Run the agent workflow
        response = await self.run(start_event=SpecializedAgentStart(input=query), ctx=ctx)

        return response.review_output

    def _create_agent_prompt(self, input: AgentReviewInput) -> str:
        """Create agent-specific prompt with context."""
        review_depth_guidelines = self._get_review_depth_guidelines(input.review_depth)
        return AGENT_PROMPT_TEMPLATE.format(
            agent_name=self.agent_name,
            focus_areas=", ".join(self.focus_areas),
            pull_request_number=input.pull_request.number,
            pull_request_title=input.pull_request.title,
            files_changed=input.files_changed,
            review_depth=input.review_depth.value,
            review_depth_guidelines=review_depth_guidelines,
        )

    def _get_review_depth_guidelines(self, review_depth: ReviewDepth) -> str:
        """Get review depth-specific guidelines for the agent."""
        match review_depth.value:
            case "basic":
                return BASIC_REVIEW_DEPTH_GUIDELINES
            case "standard":
                return STANDARD_REVIEW_DEPTH_GUIDELINES
            case "comprehensive":
                return COMPREHENSIVE_REVIEW_DEPTH_GUIDELINES

    def _parse_agent_response(self, response_content: str) -> List[FileReview]:
        """Parse agent response into structured FileReview objects using Pydantic validation."""
        try:
            # Use the YAML Pydantic parser for robust JSON/YAML parsing
            parser = YAMLPydanticOutputParser(output_cls=AgentResponseModel)
            parsed_data = parser.parse(response_content)

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
            return [
                FileReview(file_path="general", line_comments={}, summary=response_content, agent_name=self.agent_name)
            ]

    def _extract_summary(self, response_content: str) -> str:
        """Extract summary from agent response using Pydantic validation."""
        try:
            # Use the YAML Pydantic parser for robust JSON/YAML parsing
            parser = YAMLPydanticOutputParser(output_cls=AgentResponseModel)
            parsed_data = parser.parse(response_content)
            return parsed_data.summary
        except Exception:
            self.logger.error(f"Error extracting summary from agent response: {response_content}")
            return "Review completed by " + self.agent_name
