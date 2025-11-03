"""Encoding utilities for git command outputs."""


def sanitize_utf8(text: str) -> str:
    """
    Sanitize a string to ensure it contains only valid UTF-8 characters.
    
    This function handles surrogate pairs and other invalid UTF-8 sequences
    that can occur when processing file content from git commands. Surrogate
    pairs are common in binary files or files with incorrect encoding.
    
    The function uses 'replace' error handling which replaces invalid sequences
    with the Unicode replacement character (U+FFFD).
    
    Parameters
    ----------
    text : str
        The text to sanitize (may contain surrogate pairs or invalid UTF-8)
    
    Returns
    -------
    str
        Sanitized text containing only valid UTF-8 characters
    
    Examples
    --------
    >>> sanitize_utf8("Valid text")
    'Valid text'
    >>> sanitize_utf8("Text with surrogates: \\udcff\\udcfe")
    'Text with surrogates:'
    """
    if not text:
        return text
    
    # Encode to UTF-8 with 'replace' to handle surrogates, then decode back
    # This effectively replaces any invalid UTF-8 sequences (including surrogates)
    # with the replacement character (U+FFFD)
    return text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')



