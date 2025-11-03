"""API and library usage validation agent."""

from lampe.review.workflows.pr_review.agents.api_usage_agent_prompt import API_USAGE_AGENT_SYSTEM_PROMPT
from lampe.review.workflows.pr_review.agents.specialized_agent_base import SpecializedReviewAgent


class APIUsageAgent(SpecializedReviewAgent):
    """Agent specialized in validating API usage and library integration."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            agent_name="API Usage Expert",
            focus_areas=[
                "API method validation",
                "Library integration",
                "Error handling",
                "Resource management",
                "Version compatibility",
                "Deprecation warnings",
            ],
            system_prompt=API_USAGE_AGENT_SYSTEM_PROMPT,
            *args,
            **kwargs,
        )
