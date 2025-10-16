from unittest.mock import patch

from lampe.core.gitconfig import MINIMUM_GIT_VERSION, valid_git_version_available


def test_git_version_meets_requirement():
    with patch("lampe.core.gitconfig.git.Git") as mock_git:
        mock_git.return_value.version.return_value = "git version 2.50.0"

        result = valid_git_version_available()
        assert result is True
        mock_git.return_value.version.assert_called_once()


def test_git_version_below_requirement():
    with patch("lampe.core.gitconfig.git.Git") as mock_git:
        mock_git.return_value.version.return_value = "git version 2.30.0"

        result = valid_git_version_available()
        assert result is False


def test_git_version_exactly_meets_requirement():
    with patch("lampe.core.gitconfig.git.Git") as mock_git:
        mock_git.return_value.version.return_value = f"git version {MINIMUM_GIT_VERSION}"

        result = valid_git_version_available()
        assert result is True


def test_git_version_with_additional_info():
    with patch("lampe.core.gitconfig.git.Git") as mock_git:
        mock_git.return_value.version.return_value = "git version 2.50.0.windows.1"

        result = valid_git_version_available()
        assert result is True


def test_git_not_installed():
    with patch("lampe.core.gitconfig.git.Git", side_effect=Exception("Git not found")):
        result = valid_git_version_available()
        assert result is False


def test_git_command_fails():
    with patch("lampe.core.gitconfig.git.Git") as mock_git:
        mock_git.return_value.version.side_effect = Exception("Git command failed")

        result = valid_git_version_available()
        assert result is False


def test_git_version_timeout():
    with patch("lampe.core.gitconfig.git.Git") as mock_git:
        mock_git.return_value.version.side_effect = Exception("Timeout")

        result = valid_git_version_available()
        assert result is False


def test_unexpected_version_format():
    with patch("lampe.core.gitconfig.git.Git") as mock_git:
        mock_git.return_value.version.return_value = "unexpected output format"

        result = valid_git_version_available()
        assert result is False


def test_empty_version_output():
    with patch("lampe.core.gitconfig.git.Git") as mock_git:
        mock_git.return_value.version.return_value = ""

        result = valid_git_version_available()
        assert result is False


def test_git_version_with_development_suffix():
    with patch("lampe.core.gitconfig.git.Git") as mock_git:
        mock_git.return_value.version.return_value = "git version 2.50.0-rc1"

        result = valid_git_version_available()
        assert result is True
