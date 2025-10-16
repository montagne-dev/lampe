from unittest.mock import patch

import pytest

from lampe.core.utils.token import CHARACTER_TRUNCATION_THRESHOLD, truncate_to_token_limit


def test_truncate_to_token_limit_basic():
    content = "".join([f"Hello, world {i}!" for i in range(100)])
    result = truncate_to_token_limit(content, 2)
    assert result == "Hello,"


def test_truncate_to_token_limit_negative():
    content = "".join([f"Hello, world {i}!" for i in range(100)])
    with pytest.raises(ValueError):
        truncate_to_token_limit(content, -1)


def test_truncate_to_token_limit_character_limit():
    content = "a" * 250000
    total_tokens = 2

    with patch("lampe.core.utils.token.encoder") as mock_encoder:
        mock_encoder.encode.return_value = [1] * total_tokens
        mock_encoder.decode.return_value = "a" * total_tokens
        result = truncate_to_token_limit(content, 50000)

        assert len(result) == total_tokens
        assert result == "a" * total_tokens

        mock_encoder.encode.assert_called_once_with(content[:CHARACTER_TRUNCATION_THRESHOLD], disallowed_special=())
        mock_encoder.decode.assert_called_once_with(mock_encoder.encode.return_value)


@pytest.mark.skip(reason="This was for performance testing, we don't need to run it anymore")
def test_truncate_to_token_limit_benchmark(benchmark):
    content = "\n".join([f"Hello, world {i}!" for i in range(100000)])
    benchmark.pedantic(truncate_to_token_limit, args=(content, 30000), iterations=5, rounds=1)
