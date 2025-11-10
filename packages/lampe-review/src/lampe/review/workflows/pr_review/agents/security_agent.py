"""Security-focused review agent for identifying security vulnerabilities."""

from lampe.review.workflows.pr_review.agents.security_agent_prompt import SECURITY_AGENT_SYSTEM_PROMPT
from lampe.review.workflows.pr_review.agents.specialized_agent_base import SpecializedReviewAgent


class SecurityAgent(SpecializedReviewAgent):
    """Agent specialized in identifying security vulnerabilities and issues."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            agent_name="Security Expert",
            focus_areas=[
                "SQL injection prevention",
                "XSS/CSRF protection",
                "Authentication security",
                "Secret management",
                "Input validation",
                "Secure coding practices",
            ],
            system_prompt=SECURITY_AGENT_SYSTEM_PROMPT,
            *args,
            **kwargs,
        )
