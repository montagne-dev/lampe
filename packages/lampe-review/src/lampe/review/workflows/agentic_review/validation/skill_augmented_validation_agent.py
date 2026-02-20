"""Skill-augmented validation agent - with domain-specific skill content."""

from lampe.review.workflows.agentic_review.validation.validation_agent import (
    ValidationAgent,
    ValidationAgentComplete,
    ValidationAgentStart,
)

__all__ = [
    "SkillAugmentedValidationAgent",
    "ValidationAgentComplete",
    "ValidationAgentStart",
]


class SkillAugmentedValidationAgent(ValidationAgent):
    """Validation agent with skill content. The skill defines what to validate."""

    def __init__(self, skill_content: str, *args, **kwargs) -> None:
        super().__init__(skill_content=skill_content, *args, **kwargs)
