from lampe.cli.providers.base import update_or_add_text_between_tags


def test_replace_existing_tags():
    """Test replacing text between existing tags."""
    text = "Some text\n[](lampe-sdk-description-start)\nOld content\n[](lampe-sdk-description-end)\nMore text"
    new_text = "New content"
    feature = "description"

    result = update_or_add_text_between_tags(text, new_text, feature)

    expected = "Some text\n[](lampe-sdk-description-start)\nNew content\n[](lampe-sdk-description-end)\nMore text"
    assert result == expected


def test_add_tags_when_none_exist():
    """Test adding tags at the bottom when no tags exist."""
    text = "Some existing text"
    new_text = "New content"
    feature = "description"

    result = update_or_add_text_between_tags(text, new_text, feature)

    expected = "Some existing text\n\n[](lampe-sdk-description-start)\nNew content\n[](lampe-sdk-description-end)"
    assert result == expected


def test_add_tags_to_empty_text():
    """Test adding tags to empty text."""
    text = ""
    new_text = "New content"
    feature = "description"

    result = update_or_add_text_between_tags(text, new_text, feature)

    expected = "\n\n[](lampe-sdk-description-start)\nNew content\n[](lampe-sdk-description-end)"
    assert result == expected


def test_replace_with_multiline_content():
    """Test replacing with multiline content."""
    text = "Text\n[](lampe-sdk-description-start)\nOld\nContent\n[](lampe-sdk-description-end)\nEnd"
    new_text = "Line 1\nLine 2\nLine 3"
    feature = "description"

    result = update_or_add_text_between_tags(text, new_text, feature)

    expected = "Text\n[](lampe-sdk-description-start)\nLine 1\nLine 2\nLine 3\n[](lampe-sdk-description-end)\nEnd"
    assert result == expected


def test_add_with_multiline_content():
    """Test adding multiline content when no tags exist."""
    text = "Some text"
    new_text = "Line 1\nLine 2\nLine 3"
    feature = "description"

    result = update_or_add_text_between_tags(text, new_text, feature)

    expected = "Some text\n\n[](lampe-sdk-description-start)\nLine 1\nLine 2\nLine 3\n[](lampe-sdk-description-end)"
    assert result == expected


def test_different_feature_names():
    """Test with different feature names."""
    text = "Text"
    new_text = "Content"
    feature = "summary"

    result = update_or_add_text_between_tags(text, new_text, feature)

    expected = "Text\n\n[](lampe-sdk-summary-start)\nContent\n[](lampe-sdk-summary-end)"
    assert result == expected


def test_replace_only_first_occurrence():
    """Test that only the first occurrence is replaced."""
    text = (
        "Text\n[](lampe-sdk-description-start)\nFirst\n[](lampe-sdk-description-end)\n"
        "Middle\n[](lampe-sdk-description-start)\nSecond\n[](lampe-sdk-description-end)"
    )
    new_text = "Replaced"
    feature = "description"

    result = update_or_add_text_between_tags(text, new_text, feature)

    expected = (
        "Text\n[](lampe-sdk-description-start)\nReplaced\n[](lampe-sdk-description-end)\n"
        "Middle\n[](lampe-sdk-description-start)\nSecond\n[](lampe-sdk-description-end)"
    )
    assert result == expected


def test_preserve_whitespace_in_existing_tags():
    """Test that whitespace within existing tags is preserved."""
    text = "Text\n[](lampe-sdk-description-start)\n  \n  Old content  \n  \n[](lampe-sdk-description-end)\nEnd"
    new_text = "New content"
    feature = "description"

    result = update_or_add_text_between_tags(text, new_text, feature)

    expected = "Text\n[](lampe-sdk-description-start)\nNew content\n[](lampe-sdk-description-end)\nEnd"
    assert result == expected


def test_empty_new_text():
    """Test with empty new text."""
    text = "Text\n[](lampe-sdk-description-start)\nOld content\n[](lampe-sdk-description-end)\nEnd"
    new_text = ""
    feature = "description"

    result = update_or_add_text_between_tags(text, new_text, feature)

    expected = "Text\n[](lampe-sdk-description-start)\n\n[](lampe-sdk-description-end)\nEnd"
    assert result == expected


def test_add_empty_text_when_no_tags():
    """Test adding empty text when no tags exist."""
    text = "Some text"
    new_text = ""
    feature = "description"

    result = update_or_add_text_between_tags(text, new_text, feature)

    expected = "Some text\n\n[](lampe-sdk-description-start)\n\n[](lampe-sdk-description-end)"
    assert result == expected


def test_special_characters_in_content():
    """Test with special characters in content."""
    text = "Text"
    new_text = "Content with special chars: !@#$%^&*()[]{}|\\:;\"'<>,.?/~`"
    feature = "description"

    result = update_or_add_text_between_tags(text, new_text, feature)

    expected = f"Text\n\n[](lampe-sdk-description-start)\n{new_text}\n[](lampe-sdk-description-end)"
    assert result == expected


def test_unicode_content():
    """Test with unicode content."""
    text = "Text"
    new_text = "Content with unicode: 🚀 émojis and àccénts"
    feature = "description"

    result = update_or_add_text_between_tags(text, new_text, feature)

    expected = f"Text\n\n[](lampe-sdk-description-start)\n{new_text}\n[](lampe-sdk-description-end)"
    assert result == expected
