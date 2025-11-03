"""Code quality and maintainability agent."""

from lampe.review.workflows.pr_review.agents.code_quality_agent_prompt import CODE_QUALITY_AGENT_SYSTEM_PROMPT
from lampe.review.workflows.pr_review.agents.specialized_agent_base import SpecializedReviewAgent


class CodeQualityAgent(SpecializedReviewAgent):
    """Agent specialized in code quality, readability, and maintainability."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            agent_name="Code Quality Expert",
            focus_areas=[
                "Code readability",
                "Naming conventions",
                "Code organization",
                "Documentation quality",
                "Error handling",
                "Maintainability",
            ],
            system_prompt=CODE_QUALITY_AGENT_SYSTEM_PROMPT,
            *args,
            **kwargs,
        )
