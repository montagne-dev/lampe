from typing import Any, Dict, List, Optional

import pytest
from pydantic import BaseModel, ValidationError

from lampe.core.parsers.yaml_pydantic_output import YAMLParsingError, YAMLPydanticOutputParser


class SimpleModel(BaseModel):
    name: str
    age: int


class ComplexModel(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class NestedModel(BaseModel):
    user: SimpleModel
    settings: Dict[str, bool]
    items: List[int]


class NestedModelWithLiteralBlock(BaseModel):
    reasoning: str
    response: str


def test_parse_simple_yaml_success():
    parser = YAMLPydanticOutputParser(output_cls=SimpleModel)
    yaml_text = """
```yaml
name: John Doe
age: 30
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, SimpleModel)
    assert result.name == "John Doe"
    assert result.age == 30


def test_parse_yaml_with_code_blocks():
    parser = YAMLPydanticOutputParser(output_cls=SimpleModel)
    yaml_text = """
Here's the response:
```yaml
name: Jane Smith
age: 25
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, SimpleModel)
    assert result.name == "Jane Smith"
    assert result.age == 25


def test_parse_complex_yaml_with_optional_fields():
    parser = YAMLPydanticOutputParser(output_cls=ComplexModel)
    yaml_text = """
```yaml
id: 123
name: Test User
email: test@example.com
tags:
  - python
  - testing
metadata:
  active: true
  score: 95.5
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, ComplexModel)
    assert result.id == 123
    assert result.name == "Test User"
    assert result.email == "test@example.com"
    assert result.tags == ["python", "testing"]
    assert result.metadata == {"active": True, "score": 95.5}


def test_parse_yaml_with_missing_optional_fields():
    parser = YAMLPydanticOutputParser(output_cls=ComplexModel)
    yaml_text = """
```yaml
id: 456
name: Minimal User
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, ComplexModel)
    assert result.id == 456
    assert result.name == "Minimal User"
    assert result.email is None
    assert result.tags == []
    assert result.metadata == {}


def test_parse_nested_yaml_structure():
    parser = YAMLPydanticOutputParser(output_cls=NestedModel)
    yaml_text = """
```yaml
user:
  name: Nested User
  age: 40
settings:
  notifications: true
  dark_mode: false
items:
  - 1
  - 2
  - 3
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, NestedModel)
    assert result.user.name == "Nested User"
    assert result.user.age == 40
    assert result.settings == {"notifications": True, "dark_mode": False}
    assert result.items == [1, 2, 3]


def test_parse_yaml_with_special_characters():
    parser = YAMLPydanticOutputParser(output_cls=SimpleModel)
    yaml_text = """
```yaml
name: "José María O'Connor-Smith"
age: 35
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, SimpleModel)
    assert result.name == "José María O'Connor-Smith"
    assert result.age == 35


def test_parse_yaml_with_multiline_strings():
    parser = YAMLPydanticOutputParser(output_cls=ComplexModel)
    yaml_text = """
```yaml
id: 789
name: |
  Multi
  Line
  Name
email: user@test.com
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, ComplexModel)
    assert result.id == 789
    assert result.name == "Multi\nLine\nName\n"
    assert result.email == "user@test.com"


def test_parse_yaml_with_null_values():
    parser = YAMLPydanticOutputParser(output_cls=ComplexModel)
    yaml_text = """
```yaml
id: 100
name: Null Test
email: null
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, ComplexModel)
    assert result.id == 100
    assert result.name == "Null Test"
    assert result.email is None


def test_parse_yaml_with_extra_fields():
    parser = YAMLPydanticOutputParser(output_cls=SimpleModel)
    yaml_text = """
```yaml
name: John Doe
age: 30
extra_field: ignored
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, SimpleModel)
    assert result.name == "John Doe"
    assert result.age == 30


def test_parse_yaml_with_boolean_values():
    parser = YAMLPydanticOutputParser(output_cls=ComplexModel)
    yaml_text = """
```yaml
id: 200
name: Boolean Test
metadata:
  flag1: true
  flag2: false
  flag3: yes
  flag4: no
  flag5: on
  flag6: off
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, ComplexModel)
    assert result.metadata["flag1"] is True
    assert result.metadata["flag2"] is False
    assert result.metadata["flag3"] is True
    assert result.metadata["flag4"] is False
    assert result.metadata["flag5"] is True
    assert result.metadata["flag6"] is False


def test_parse_yaml_with_numeric_types():
    parser = YAMLPydanticOutputParser(output_cls=ComplexModel)
    yaml_text = """
```yaml
id: 300
name: Numeric Test
metadata:
  integer: 42
  float: 3.14159
  scientific: 1.23e-4
  negative: -100
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, ComplexModel)
    assert result.metadata["integer"] == 42
    assert result.metadata["float"] == 3.14159
    assert abs(result.metadata["scientific"] - 1.23e-4) < 1e-10
    assert result.metadata["negative"] == -100


def test_parse_yaml_with_arrays_and_nested_objects():
    parser = YAMLPydanticOutputParser(output_cls=ComplexModel)
    yaml_text = """
```yaml
id: 400
name: Complex Test
tags:
  - tag1
  - tag2
metadata:
  nested:
    level1:
      level2: deep_value
  array_of_objects:
    - name: item1
      value: 10
    - name: item2
      value: 20
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, ComplexModel)
    assert result.tags == ["tag1", "tag2"]
    assert result.metadata["nested"]["level1"]["level2"] == "deep_value"
    assert len(result.metadata["array_of_objects"]) == 2
    assert result.metadata["array_of_objects"][0]["name"] == "item1"


def test_parse_yaml_with_comments_ignored():
    parser = YAMLPydanticOutputParser(output_cls=SimpleModel)
    yaml_text = """
```yaml
# This is a comment
name: Comment Test  # inline comment
age: 25
# Another comment
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, SimpleModel)
    assert result.name == "Comment Test"
    assert result.age == 25


def test_parse_malformed_yaml_code_block():
    parser = YAMLPydanticOutputParser(output_cls=SimpleModel)
    yaml_text = """
Here's some text
```yaml
name: Test
age: 30
```More text after

"""
    result = parser.parse(yaml_text)
    assert isinstance(result, SimpleModel)
    assert result.name == "Test"
    assert result.age == 30


def test_parse_yaml_with_quotes_and_escapes():
    parser = YAMLPydanticOutputParser(output_cls=ComplexModel)
    yaml_text = """
```yaml
id: 500
name: 'Single quoted name'
email: "double@quoted.com"
metadata:
  escaped_string: "Line 1\\nLine 2\\tTabbed"
  special_chars: "Symbols: !@#$%^&*()"
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, ComplexModel)
    assert result.name == "Single quoted name"
    assert result.email == "double@quoted.com"
    assert "Line 1\nLine 2\tTabbed" in result.metadata["escaped_string"]


def test_parse_empty_yaml():
    parser = YAMLPydanticOutputParser(output_cls=ComplexModel)
    yaml_text = ""

    with pytest.raises(YAMLParsingError):
        parser.parse(yaml_text)


def test_parse_invalid_yaml_syntax():
    parser = YAMLPydanticOutputParser(output_cls=SimpleModel)
    yaml_text = """
```yaml
name: John Doe
age: 30
  invalid_indentation: true
```
"""
    with pytest.raises(YAMLParsingError):
        parser.parse(yaml_text)


def test_parse_yaml_with_invalid_data_type():
    parser = YAMLPydanticOutputParser(output_cls=SimpleModel)
    yaml_text = """
```yaml
name: John Doe
age: "not a number"
```
"""
    with pytest.raises(ValidationError):
        parser.parse(yaml_text)


def test_parse_yaml_missing_required_field():
    parser = YAMLPydanticOutputParser(output_cls=SimpleModel)
    yaml_text = """
```yaml
name: John Doe
```
"""
    with pytest.raises(ValidationError):
        parser.parse(yaml_text)


def test_parse_fallback_to_code_block_when_yaml_fails():
    """Test that parser falls back to extract_md_code_block when extract_yaml fails."""
    parser = YAMLPydanticOutputParser(output_cls=SimpleModel)
    # Text that would fail extract_yaml but succeed with extract_md_code_block
    yaml_text = """
Some text before
```
name: Fallback Test
age: 42
```
More text after
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, SimpleModel)
    assert result.name == "Fallback Test"
    assert result.age == 42


def test_parse_yaml_with_nested_yaml_block_in_literal():
    """Test parsing YAML with a nested YAML block inside a literal block."""
    parser = YAMLPydanticOutputParser(output_cls=SimpleModel)
    yaml_text = """
```yaml
name: |
    ```yaml
     something: true
     ```
age: 30
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, SimpleModel)
    assert result.name.strip() == "```yaml\n something: true\n ```"
    assert result.age == 30


def test_parse_yaml_with_nested_yaml_block_in_literal_and_text():
    """Test parsing YAML with a nested YAML block inside a literal block and text."""
    parser = YAMLPydanticOutputParser(output_cls=NestedModelWithLiteralBlock)
    yaml_text = """
```yaml
reasoning: |
  text here

response: |
  Here\'s how to update the PR:
  1. Find this line in the code:
  ```df.to_html(na_rep="", index=True, escape=False)```

  2. Change it to:
  ```df.to_html(na_rep="", index=True, escape=True)```

  Let me know if you need help with anything else.
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, NestedModelWithLiteralBlock)
    assert result.reasoning.strip() == "text here"
    assert "Here's how to update the PR:" in result.response.strip()
    assert "1. Find this line in the code:" in result.response.strip()
    assert '```df.to_html(na_rep="", index=True, escape=False)```' in result.response.strip()
    assert "2. Change it to:" in result.response.strip()
    assert '```df.to_html(na_rep="", index=True, escape=True)```' in result.response.strip()
    assert "Let me know if you need help with anything else." in result.response.strip()


def test_parse_fallback_with_non_yaml_code_block():
    """Test fallback behavior with generic code block containing valid YAML."""
    parser = YAMLPydanticOutputParser(output_cls=ComplexModel)
    yaml_text = """
Here's the configuration:
```
id: 600
name: Fallback Complex
email: fallback@test.com
tags:
  - fallback
  - testing
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, ComplexModel)
    assert result.id == 600
    assert result.name == "Fallback Complex"
    assert result.email == "fallback@test.com"
    assert result.tags == ["fallback", "testing"]


def test_parse_fallback_with_nested_code_blocks():
    """Test fallback behavior with nested code blocks in content."""
    parser = YAMLPydanticOutputParser(output_cls=ComplexModel)
    yaml_text = """
Configuration details:
```
id: 700
name: Nested Test
metadata:
  example_code: |
    ```python
    print("Hello World")
    ```
  description: "Contains nested code"
```
"""
    result = parser.parse(yaml_text)
    assert isinstance(result, ComplexModel)
    assert result.id == 700
    assert result.name == "Nested Test"
    assert "```python" in result.metadata["example_code"]


def test_parse_fallback_fails_with_invalid_yaml():
    """Test that both primary and fallback parsing fail with invalid YAML."""
    parser = YAMLPydanticOutputParser(output_cls=SimpleModel)
    yaml_text = """
```
name: Test
age: 30
  invalid_indentation: true
```
"""
    with pytest.raises(YAMLParsingError):
        parser.parse(yaml_text)


def test_parse_fallback_no_code_block():
    """Test parsing when no code block is present in the text."""
    parser = YAMLPydanticOutputParser(output_cls=SimpleModel)
    yaml_text = """
name: Test
age: 30
"""

    result = parser.parse(yaml_text)
    assert isinstance(result, SimpleModel)
    assert result.name == "Test"
    assert result.age == 30
