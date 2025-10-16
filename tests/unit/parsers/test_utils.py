import pytest
import yaml

from lampe.core.parsers.utils import extract_md_code_block


def test_extract_yaml_with_inner_yaml_block():
    input_text = """This is a clear sentence
```python
print("Hello, world!")
```
Another one explain stuff

```yaml
reasoning: |
  Explain your thought process about the developer's response and how it affects your understanding
  of the code change. This helps maintain transparency in the review process.
  ```json
  {
    "foo": "bar"
  }
  ```
response: |
  Your actual response to the developer.
  ```python
  print("Hello, world!")
  ```
  ```yaml
  foo: bar
  ```
```
"""
    expected = """reasoning: |
  Explain your thought process about the developer's response and how it affects your understanding
  of the code change. This helps maintain transparency in the review process.
  ```json
  {
    "foo": "bar"
  }
  ```
response: |
  Your actual response to the developer.
  ```python
  print("Hello, world!")
  ```
  ```yaml
  foo: bar
  ```"""
    assert extract_md_code_block(input_text, "yaml") == expected


def test_extract_yaml_indentation_of_text():
    input_text = """This is a clear sentence
```python
print("Hello, world!")
```
Another one explain stuff
```yaml
reasoning: |
  Explain your thought process about the developer's response and how it affects your understanding
  of the code change. This helps maintain transparency in the review process.
    ```json
    {
        "foo": "bar"
    }
    ```
response: |
Your actual response to the developer.
    ```python
    print("Hello, world!")
    ```
```

More explanation
"""

    expected = """reasoning: |
  Explain your thought process about the developer's response and how it affects your understanding
  of the code change. This helps maintain transparency in the review process.
    ```json
    {
        "foo": "bar"
    }
    ```
response: |
Your actual response to the developer.
    ```python
    print("Hello, world!")
    ```"""
    assert extract_md_code_block(input_text, "yaml") == expected


def test_extract_yaml_not_valid_yaml():
    input_text = """This is a clear sentence
```python
print("Hello, world!")
```
Another one explain stuff
```yaml
reasoning: |
  Explain your thought process about the developer's response and how it affects your understanding
  of the code change. This helps maintain transparency in the review process.
    ```json
    {
        "foo": "bar"
    }
    ```
response: |
Your actual response to the developer.
```python
print("Hello, world!")
```
```

More explanation
"""

    expected = """reasoning: |
  Explain your thought process about the developer's response and how it affects your understanding
  of the code change. This helps maintain transparency in the review process.
    ```json
    {
        "foo": "bar"
    }
    ```
response: |
Your actual response to the developer."""
    assert extract_md_code_block(input_text, "yaml") == expected


def test_extract_md_code_block_generic():
    """Test extracting from generic code block without language specification."""
    input_text = """Some text before
```
key: value
number: 42
```
Text after"""
    expected = """key: value
number: 42"""
    assert extract_md_code_block(input_text) == expected


def test_extract_md_code_block_generic_only_code():
    """Only code block, no text before or after."""
    input_text = """```
key: value
number: 42
```"""
    expected = """key: value
number: 42"""
    assert extract_md_code_block(input_text) == expected


def test_extract_md_code_block_with_language():
    """Test extracting code block with specific language."""
    input_text = """Some text before
```python
print("Hello, world!")
x = 42
```
Text after"""
    expected = """print("Hello, world!")
x = 42"""
    assert extract_md_code_block(input_text, "python") == expected


def test_extract_md_code_block_with_nested_blocks():
    """Test extracting code block containing nested code blocks."""
    input_text = """Configuration:
```yaml
data: |
  Some multiline data
  ```json
  {"nested": "content"}
  ```
  More data
```
End"""
    expected = """data: |
  Some multiline data
  ```json
  {"nested": "content"}
  ```
  More data"""
    assert extract_md_code_block(input_text, "yaml") == expected


def test_extract_md_code_block_empty():
    """Test extracting empty code block."""
    input_text = """Configuration:
```yaml

```
End"""
    expected = ""
    assert extract_md_code_block(input_text, "yaml") == expected


def test_extract_md_code_block_empty_full():
    """Test extracting empty code block."""
    input_text = """Configuration:
```yaml
```
End"""
    expected = None
    assert extract_md_code_block(input_text, "yaml") == expected


def test_extract_md_code_block_no_match():
    """Test that None is returned when no matching code block is found."""
    input_text = """Just plain text
No code blocks here
```wronglang
some content
```"""
    # When looking for "python" but only "wronglang" exists
    assert extract_md_code_block(input_text, "python") is None


def test_extract_md_code_block_empty_language():
    """Test extracting any code block when language is empty string."""
    input_text = """Text before
```
generic content
```
Text after"""
    expected = """generic content"""
    assert extract_md_code_block(input_text, "") == expected


def test_extract_md_code_block_match_any_language():
    """Test extracting any code block when language is empty string."""
    input_text = """Text before
```randomlanguage
generic content
```
Text after"""
    expected = """generic content"""
    assert extract_md_code_block(input_text, match_any_language=True) == expected


def test_extract_md_code_block_case_insensitive():
    """Test that language matching is case insensitive."""
    input_text = """Text before
```YAML
key: value
```
Text after"""
    expected = """key: value"""
    assert extract_md_code_block(input_text, "yaml") == expected


@pytest.mark.skip("no need to run this benchmark again, it has been validated already")
def test_benchmark_extract_md_code_block_with_long_attributes(benchmark):
    """Benchmark test for parsing YAML with many attributes.

    Benchmark results:
    - Min: 242.1071 ms
    - Max: 264.8239 ms
    - Mean: 251.9800 ms
    - StdDev: 9.5591
    - Median: 247.9024 ms
    - IQR: 15.5057
    - Outliers: 2;0
    - OPS: 3.9686
    - Rounds: 5
    - Iterations: 1
    """
    long_attributes = [f"  description_{i}: 'value_{i}'" for i in range(100001)]
    long_attributes_str = "\n".join(long_attributes)
    yaml_text = f"""
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
{long_attributes_str}
```
"""

    def parse_yaml():
        return extract_md_code_block(yaml_text)

    result = benchmark(parse_yaml)
    data = yaml.safe_load(result)
    assert len(data["metadata"]) >= 10000
