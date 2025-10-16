from unittest.mock import patch

from lampe.cli.providers.base import PRDescriptionPayload
from lampe.cli.providers.console import ConsoleProvider


def test_console_provider_init(sample_repository, sample_pull_request):
    """Test ConsoleProvider initialization with default format."""
    provider = ConsoleProvider(repository=sample_repository, pull_request=sample_pull_request)

    assert provider.repository == sample_repository
    assert provider.pull_request == sample_pull_request


@patch("builtins.print")
def test_console_provider_deliver_pr_description_text_format(mock_print, sample_repository, sample_pull_request):
    """Test deliver_pr_description with text format."""
    provider = ConsoleProvider(repository=sample_repository, pull_request=sample_pull_request)

    payload = PRDescriptionPayload(description="Test PR description")
    provider.deliver_pr_description(payload)

    # Verify print was called with the description
    mock_print.assert_called_once_with("Test PR description")
