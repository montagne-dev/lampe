"""Design pattern and architectural consistency agent."""

from lampe.review.workflows.pr_review.agents.design_pattern_agent_prompt import DESIGN_PATTERN_AGENT_SYSTEM_PROMPT
from lampe.review.workflows.pr_review.agents.specialized_agent_base import SpecializedReviewAgent


class DesignPatternAgent(SpecializedReviewAgent):
    """Agent specialized in validating design patterns and architectural consistency."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            agent_name="Architecture Expert",
            focus_areas=[
                "SOLID principles",
                "Design patterns",
                "Architectural consistency",
                "Separation of concerns",
                "Dependency management",
                "Code organization",
            ],
            system_prompt=DESIGN_PATTERN_AGENT_SYSTEM_PROMPT,
            *args,
            **kwargs,
        )
