"""Testing strategy and coverage agent."""

from lampe.review.workflows.pr_review.agents.specialized_agent_base import SpecializedReviewAgent
from lampe.review.workflows.pr_review.agents.testing_agent_prompt import TESTING_AGENT_SYSTEM_PROMPT


class TestingAgent(SpecializedReviewAgent):
    """Agent specialized in testing strategy, coverage, and test quality."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            agent_name="Testing Expert",
            focus_areas=[
                "Test coverage",
                "Test quality",
                "Edge case testing",
                "Integration testing",
                "Test organization",
                "Test maintainability",
            ],
            system_prompt=TESTING_AGENT_SYSTEM_PROMPT,
            *args,
            **kwargs,
        )
