from llama_index.core.types import BaseOutputParser

from lampe.core.parsers.utils import extract_md_code_block


class MarkdownCodeBlockRemoverOutputParser(BaseOutputParser):
    """
    Output parser that extracts and returns the content of markdown code blocks marked with 'md' or 'markdown'.

    This parser is designed to process LLM outputs or other text that may contain markdown code blocks.
    It specifically targets code blocks with the language tag 'md' or 'markdown', removing the code block
    markers and returning only the inner content. If no such block is found, it falls back to extracting
    a generic code block (```). If the result still contains any other code block (with a language tag),
    it is preserved as-is. If no code block is found, the original text (stripped of leading/trailing whitespace)
    is returned.
    Edge Cases:
    - If the input is an empty string, returns an empty string.
    - If the input contains a code block with a language other than 'md' or 'markdown', it is preserved.
    - If the input contains text before or after a markdown code block, only the content inside the block is returned.
    - If the input contains an incomplete code block, returns the input with the trailing backticks removed if present.

    Examples
    --------
    >>> parser = MarkdownCodeBlockRemoverOutputParser()
    >>> text = '''```md
    ... This is inside md block.
    ... ```'''
    >>> parser.parse(text)
    'This is inside md block.'

    >>> text = '''```python
    ... Multiple lines
    ... are here.
    ... ```'''
    >>> parser.parse(text)
    '```python\nMultiple lines\nare here.\n```'

    >>> text = 'No code block here.'
    >>> parser.parse(text)
    'No code block here.'
    """

    def parse(self, output: str) -> str:
        """
        Extracts and returns the content of a markdown code block marked with ```md or ```markdown from the input text.

        If the input contains a markdown code block with language tag 'md' or 'markdown',
        the content inside that block is returned, with the code block markers removed.
        If no such block is found, but a generic code block (```) is present, its content is returned.
        If the result still contains any other code block (with a language tag), it is preserved as-is.
        If no code block is found, the original text (stripped of leading/trailing whitespace) is returned.
        """
        if output == "":
            return output
        # Try to extract content from markdown code blocks with specific languages
        content = (
            extract_md_code_block(output, "md")
            or extract_md_code_block(output, "markdown")
            or extract_md_code_block(output, "")
        ) or output.strip()

        if extract_md_code_block(content, match_any_language=True) is not None:
            # if there is any other remaining code block, we don't want to remove triple backticks
            return content

        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content
