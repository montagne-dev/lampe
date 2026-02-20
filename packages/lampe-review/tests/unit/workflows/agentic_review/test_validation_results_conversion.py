"""Unit tests for validation results to agent review output conversion."""

from lampe.review.workflows.agentic_review.agentic_review_workflow import (
    _validation_results_to_agent_review_output,
)
from lampe.review.workflows.agentic_review.data_models import (
    ValidationFinding,
    ValidationResult,
)


def test_validation_results_produce_only_structured_comments():
    """Conversion must not duplicate findings into line_comments (avoids duplicate issues in aggregator)."""
    results = [
        ValidationResult(
            task_id="basic-1",
            findings=[
                ValidationFinding(
                    file_path="src/page.astro",
                    line_number=7,
                    action="fix",
                    problem_summary="Missing getStaticPaths",
                    severity="high",
                    category="logic",
                ),
            ],
            no_issue=False,
            sources=[],
        ),
    ]
    agent_outputs = _validation_results_to_agent_review_output(results)
    assert len(agent_outputs) == 1
    assert len(agent_outputs[0].reviews) == 1
    fr = agent_outputs[0].reviews[0]
    assert fr.structured_comments
    assert len(fr.structured_comments) == 1
    assert fr.structured_comments[0].comment == "Missing getStaticPaths"
    assert fr.structured_comments[0].severity == "high"
    assert fr.structured_comments[0].category == "logic"
    # Must be empty so aggregator does not show each finding twice (logic + line_comment)
    assert fr.line_comments == {}
