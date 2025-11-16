"""Design pattern and architectural consistency agent."""

from llama_index.core.workflow import Context, step

from lampe.core.workflows.function_calling_agent import UserInputEvent
from lampe.review.workflows.pr_review.agents.default_agent_prompt import (
    DEFAULT_AGENT_SYSTEM_PROMPT,
    PR_REVIEW_USER_PROMPT,
)
from lampe.review.workflows.pr_review.agents.specialized_agent_base import SpecializedAgentStart, SpecializedReviewAgent


class DefaultAgent(SpecializedReviewAgent):
    """Agent specialized in validating design patterns and architectural consistency."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            agent_name="Default Agent",
            focus_areas=[
                "Code quality",
                "Code readability",
                "Code organization",
                "Code maintainability",
                "Code performance",
            ],
            system_prompt=DEFAULT_AGENT_SYSTEM_PROMPT,
            *args,
            **kwargs,
        )

    @step
    async def setup_query_and_tools(self, ctx: Context, ev: SpecializedAgentStart) -> UserInputEvent:
        """Setup the query and tools for the specialized agent."""
        query = PR_REVIEW_USER_PROMPT.format(
            pull_request=ev.input.pull_request,
            working_dir=ev.input.repository.local_path,
            files_changed=ev.input.files_changed,
            custom_guidelines_section="",
        )
        self.update_tools(partial_params={"repo_path": ev.input.repository.local_path, "include_line_numbers": True})
        return UserInputEvent(input=query)
