"""Unit tests for LLM response parsing (malformed/truncated JSON handling)."""

from lampe.review.workflows.agentic_review.response_parse import (
    extract_json_from_llm_content,
    parse_validation_response,
)


def test_extract_json_from_plain_content():
    """When no markdown block, return stripped content."""
    content = '  {"no_issue": true, "findings": []}  '
    assert extract_json_from_llm_content(content) == '{"no_issue": true, "findings": []}'


def test_extract_json_from_markdown_json_block():
    """Extract JSON from ```json ... ``` block."""
    content = """Here is the result:

```json
{"no_issue": false, "findings": [{"file_path": "a.py", "line_number": 1}]}
```
"""
    assert '{"no_issue": false' in extract_json_from_llm_content(content)
    assert "findings" in extract_json_from_llm_content(content)


def test_extract_json_from_generic_code_block():
    """Extract from ``` ... ``` without json tag."""
    content = """```
{"no_issue": true, "findings": []}
```
"""
    result = extract_json_from_llm_content(content)
    assert '"no_issue"' in result
    assert '"findings"' in result


def test_extract_json_empty_content():
    """Empty or whitespace returns empty string."""
    assert extract_json_from_llm_content("") == ""
    assert extract_json_from_llm_content("   \n  ") == ""


def test_parse_validation_response_valid_json():
    """Valid JSON returns parsed model and success."""
    content = '{"no_issue": true, "findings": []}'
    parsed, success = parse_validation_response(content)
    assert success
    assert parsed is not None
    assert parsed.no_issue is True
    assert parsed.findings == []


def test_parse_validation_response_with_findings():
    """Valid JSON with findings parses correctly."""
    content = """{"no_issue": false, "findings": [
        {"file_path": "src/a.py", "line_number": 42, "action": "fix",
         "problem_summary": "Missing validation", "severity": "high", "category": "security"}
    ]}"""
    parsed, success = parse_validation_response(content)
    assert success
    assert parsed is not None
    assert parsed.no_issue is False
    assert len(parsed.findings) == 1
    assert parsed.findings[0]["file_path"] == "src/a.py"
    assert parsed.findings[0]["line_number"] == 42


def test_parse_validation_response_malformed_json_no_exception():
    """Malformed JSON returns (None, False) without raising."""
    malformed = '{\n  "reviews": [\n    {...Output."\n    }\n  ]\n}'
    parsed, success = parse_validation_response(malformed)
    assert not success
    assert parsed is None


def test_parse_validation_response_truncated_json_no_exception():
    """Truncated JSON returns (None, False) without raising."""
    truncated = '{"no_issue": false, "findings": [{"file_path": "x'
    parsed, success = parse_validation_response(truncated)
    assert not success
    assert parsed is None


def test_parse_validation_response_empty_no_exception():
    """Empty content returns (None, False) without raising."""
    parsed, success = parse_validation_response("")
    assert not success
    assert parsed is None


def test_parse_validation_response_garbage_no_exception():
    """Arbitrary garbage returns (None, False) without raising."""
    for garbage in ["not json at all", "null", "[]", '{"x"}', "}{"]:
        parsed, success = parse_validation_response(garbage)
        assert not success, f"Expected failure for input: {garbage!r}"
        assert parsed is None


def test_validation_agent_parse_response_graceful_fallback():
    """ValidationAgent._parse_response returns empty findings on malformed input (no traceback)."""
    from lampe.review.workflows.agentic_review.validation.validation_agent import ValidationAgent

    agent = ValidationAgent(skill_content="")
    findings, no_issue = agent._parse_response(
        '{\n  "reviews": [\n    {...Output."\n    }\n  ]\n}',
        sources=[],
    )
    assert findings == []
    assert no_issue is True


def test_quick_review_agent_parse_response_graceful_fallback():
    """QuickReviewAgent._parse_response returns empty findings on malformed input (no traceback)."""
    from lampe.review.workflows.quick_review.quick_review_agent import QuickReviewAgent

    agent = QuickReviewAgent()
    findings, no_issue = agent._parse_response(
        '{"no_issue": true, "findings": [{"incomplete',
        sources=[],
    )
    assert findings == []
    assert no_issue is True
