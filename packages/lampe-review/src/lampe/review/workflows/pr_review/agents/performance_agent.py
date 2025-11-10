"""Performance analysis and optimization agent."""

from lampe.review.workflows.pr_review.agents.performance_agent_prompt import PERFORMANCE_AGENT_SYSTEM_PROMPT
from lampe.review.workflows.pr_review.agents.specialized_agent_base import SpecializedReviewAgent


class PerformanceAgent(SpecializedReviewAgent):
    """Agent specialized in identifying performance issues and optimization opportunities."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            agent_name="Performance Expert",
            focus_areas=[
                "Algorithmic complexity",
                "Memory optimization",
                "Database performance",
                "Resource efficiency",
                "Caching strategies",
                "Async operations",
            ],
            system_prompt=PERFORMANCE_AGENT_SYSTEM_PROMPT,
            *args,
            **kwargs,
        )
