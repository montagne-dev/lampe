import logging

import tiktoken

CHARACTER_TRUNCATION_THRESHOLD = 200000

encoder = tiktoken.encoding_for_model("gpt-4.1")
logger = logging.getLogger(__name__)


def count_token_string(content: str) -> int:
    return len(encoder.encode(content))


def safe_truncate(text: str, limit: int) -> str:
    return "".join(list(text)[:limit])


def truncate_to_token_limit(content: str, max_tokens: int) -> str:
    """Truncate the content to the maximum number of tokens.
    If the content is too long, truncate it to 200000 characters (3-4 characters per token)
    before encoding for performance reasons.
    We allow `endoftext` token to be encoded, since in the past we encountered issues with the tokenizer.

    Args:
        content (str): The content to truncate.
        max_tokens (int): The maximum number of tokens to keep.

    Returns:
        str: The truncated content.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be a positive integer")
    if len(content) >= CHARACTER_TRUNCATION_THRESHOLD:
        logger.warning(
            f"Truncating content to {CHARACTER_TRUNCATION_THRESHOLD} characters before encoding "
            f"for performance reasons. Content length: {len(content)}"
        )
        content = safe_truncate(content, CHARACTER_TRUNCATION_THRESHOLD)
    tokens = encoder.encode(
        content,
        disallowed_special=(),
    )
    truncated = encoder.decode(tokens[:max_tokens])
    return truncated
