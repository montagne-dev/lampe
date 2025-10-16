import pytest

from lampe.core.parsers.markdown_code_block_remover_output import MarkdownCodeBlockRemoverOutputParser


@pytest.mark.parametrize(
    "input_text,expected",
    [
        ("", ""),
        ("""```md\nThis is inside md block.\n```""", "This is inside md block."),
        ("""```markdown\nThis is inside markdown block.\n```""", "This is inside markdown block."),
        ("""```markdown\nMultiple lines\nare here.\n```""", "Multiple lines\nare here."),
        ("No code block here.", "No code block here."),
        ("""```python\nprint('not md or markdown')\n```""", """```python\nprint('not md or markdown')\n```"""),
        (
            """Some text before\n```md\nShould not match because not at start.\n```\nSome text after""",
            """Should not match because not at start.""",
        ),
        ("""Some text before\n```python\nvar = 5\n```""", """Some text before\n```python\nvar = 5\n```"""),
        ("""some text\n```""", "some text\n"),
        ("""```\nsome text""", "\nsome text"),
    ],
)
def test_markdown_code_block_remover_output_parser(input_text, expected):
    parser = MarkdownCodeBlockRemoverOutputParser()

    assert parser.parse(input_text) == expected
