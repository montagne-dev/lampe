import re

MARKDOWN_CODE_BLOCK_PATTERN = (
    r"(?:.*?\n)?```{language}\n((?:[^`]|`(?!``)|``(?!`)|```(?!`)|\n\s+```[a-zA-Z]*[\s\S]*?\n\s+```)*?)\n```"
)
MARKDOWN_CODE_BLOCK_MATCH_ANY_LANGUAGE_PATTERN = r"[\w-]*"


def extract_md_code_block(output: str, language: str = "", match_any_language: bool = False) -> str | None:
    """Extract markdown code block content from a string, handling nested code blocks.

    Parameters
    ----------
    output : str
        The string to extract code block content from.
    language : str
        The language identifier for the code block (e.g., 'yaml', 'python', 'json').
    match_any_language : bool
        If True, the language of the code block is optional and the function will return the first code block found.
    Returns
    -------
    :
        The extracted code block content, or the entire input if no language is specified
        or no matching code block is found.

    Notes
    -----
    This function extracts content between ```{language} tags, preserving any nested
    code blocks within the content. The regex pattern handles:
    - Optional text before the code block
    - Nested code blocks (e.g. ```json, ```python, ``` inside the main block)
    - Proper indentation of nested content
    - Case-insensitive language tag matching

    Examples
    --------
    >>> text = '''
    ... Some text
    ... ```yaml
    ... key: value
    ... nested: |
    ...   ```python
    ...   print("Hello")
    ...   ```
    ... ```
    ... '''
    >>> result = extract_md_code_block(text, 'yaml')
    >>> print(result)
    key: value
    nested: |
      ```python
      print("Hello")
      ```
    """

    if match_any_language:
        code_block_pattern = MARKDOWN_CODE_BLOCK_PATTERN.format(language=MARKDOWN_CODE_BLOCK_MATCH_ANY_LANGUAGE_PATTERN)
    else:
        code_block_pattern = MARKDOWN_CODE_BLOCK_PATTERN.format(language=language)

    result = re.search(code_block_pattern, output, re.MULTILINE | re.IGNORECASE | re.DOTALL)
    if result:
        return result.group(1)
    return None
