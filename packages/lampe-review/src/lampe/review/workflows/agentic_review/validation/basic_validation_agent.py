"""Basic validation agent - no skill augmentation."""

from lampe.review.workflows.agentic_review.validation.validation_agent import (
    ValidationAgent,
    ValidationAgentComplete,
    ValidationAgentStart,
)

__all__ = ["BasicValidationAgent", "ValidationAgentComplete", "ValidationAgentStart"]


class BasicValidationAgent(ValidationAgent):
    """Validation agent without skill content. Executes orchestrator-formulated tasks."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(skill_content="", *args, **kwargs)
