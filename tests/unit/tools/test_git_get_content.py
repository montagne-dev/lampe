from unittest.mock import MagicMock

import pytest
from git import GitCommandError, Repo

from lampe.core.tools.repository import get_file_content_at_commit


@pytest.fixture
def mock_repo():
    mock = MagicMock(spec=Repo)
    mock.git_dir = "/tmp/test_repo/.git"
    return mock


@pytest.fixture
def mock_commits_availability():
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_context)
    mock_context.__exit__ = MagicMock(return_value=None)
    return mock_context


def test_get_file_content_success(mocker, mock_repo, mock_commits_availability):
    """Test successful file content retrieval"""
    content = "line1\nline2\nline3"
    mock_repo.git.show.return_value = content
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mock_repo_class = mocker.patch("lampe.core.tools.repository.content.Repo", return_value=mock_repo)
    fake_path = "/tmp/fake_repo"
    result = get_file_content_at_commit("main", "test.py", repo_path=fake_path)
    assert result == "line1\nline2\nline3"
    mock_repo.git.show.assert_called_once_with("main:test.py")
    mock_repo_class.assert_called_once_with(path=fake_path)


def test_get_file_content_path_not_found(mocker, mock_repo, mock_commits_availability):
    """Test that GitCommandError is raised when file doesn't exist"""
    mock_repo.git.show.side_effect = GitCommandError("test", stderr="fatal: path missing.py does not exist")
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mocker.patch("lampe.core.tools.repository.content.Repo", return_value=mock_repo)
    with pytest.raises(GitCommandError):
        get_file_content_at_commit("main", "missing.py", repo_path="/tmp/fake_repo")
    mock_repo.git.show.assert_called_once_with("main:missing.py")


def test_get_file_content_commit_not_found(mocker, mock_repo, mock_commits_availability):
    mock_repo.git.show.side_effect = GitCommandError(
        "git",
        stderr="fatal: invalid object name '81212e0574841c9dbac39aefadc8277ab5fa'.",
        status=128,
    )
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mocker.patch("lampe.core.tools.repository.content.Repo", return_value=mock_repo)
    with pytest.raises(GitCommandError) as exc_info:
        get_file_content_at_commit("81212e0574841c9dbac39aefadc8277ab5fa", "pyproject.toml", repo_path="/tmp/fake_repo")

    assert "invalid object name" in str(exc_info.value)
    mock_repo.git.show.assert_called_once_with("81212e0574841c9dbac39aefadc8277ab5fa:pyproject.toml")


def test_get_file_content_at_commit_success(mocker, mock_commits_availability):
    """Test successful file content retrieval"""
    content = "line1\nline2\nline3"
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git_dir = "/tmp/test_repo/.git"
    mock_repo.return_value.git.show.return_value = content

    result = get_file_content_at_commit("main", "test.py", repo_path="/path/to/repo")
    assert result == content
    mock_repo.return_value.git.show.assert_called_once_with("main:test.py")


def test_get_file_content_at_commit_with_line_range(mocker, mock_commits_availability):
    """Test file content retrieval with line range"""
    content = "line1\nline2\nline3\nline4\nline5"
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git.show.return_value = content

    result = get_file_content_at_commit("main", "test.py", line_start=1, line_end=3, repo_path="/path/to/repo")
    assert result == "line2\nline3\nline4"
    mock_repo.return_value.git.show.assert_called_once_with("main:test.py")


def test_get_file_content_at_commit_with_single_line(mocker, mock_commits_availability):
    """Test file content retrieval when line_start equals line_end"""
    content = "line1\nline2\nline3\nline4\nline5"
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git.show.return_value = content

    result = get_file_content_at_commit("main", "test.py", line_start=2, line_end=2, repo_path="/path/to/repo")
    assert result == "line3"
    mock_repo.return_value.git.show.assert_called_once_with("main:test.py")


def test_get_file_content_at_commit_git_error(mocker, mock_commits_availability):
    """Test GitCommandError is raised on unexpected git errors"""
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git.show.side_effect = GitCommandError("show", status=1)

    with pytest.raises(GitCommandError):
        get_file_content_at_commit("main", "test.py", repo_path="/path/to/repo")

    mock_repo.return_value.git.show.assert_called_once_with("main:test.py")
