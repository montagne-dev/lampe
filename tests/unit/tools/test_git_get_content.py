from unittest.mock import MagicMock

import pytest
from git import GitCommandError, Repo

from lampe.core.tools.repository import get_file_content_at_commit
from lampe.core.tools.repository.content import list_directory_at_commit


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
    mocker.patch("lampe.core.tools.repository.content.get_file_size_at_commit", return_value=100)
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
    mocker.patch("lampe.core.tools.repository.content.get_file_size_at_commit", return_value=100)
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
    mocker.patch("lampe.core.tools.repository.content.get_file_size_at_commit", return_value=100)
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mocker.patch("lampe.core.tools.repository.content.Repo", return_value=mock_repo)
    with pytest.raises(GitCommandError) as exc_info:
        get_file_content_at_commit("81212e0574841c9dbac39aefadc8277ab5fa", "pyproject.toml", repo_path="/tmp/fake_repo")

    assert "invalid object name" in str(exc_info.value)
    mock_repo.git.show.assert_called_once_with("81212e0574841c9dbac39aefadc8277ab5fa:pyproject.toml")


def test_get_file_content_at_commit_success(mocker, mock_commits_availability):
    """Test successful file content retrieval"""
    content = "line1\nline2\nline3"
    mocker.patch("lampe.core.tools.repository.content.get_file_size_at_commit", return_value=100)
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
    mocker.patch("lampe.core.tools.repository.content.get_file_size_at_commit", return_value=100)
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git.show.side_effect = GitCommandError("show", status=1)

    with pytest.raises(GitCommandError):
        get_file_content_at_commit("main", "test.py", repo_path="/path/to/repo")

    mock_repo.return_value.git.show.assert_called_once_with("main:test.py")


def test_list_directory_at_commit_root_uses_commit_only(mocker, mock_commits_availability):
    """Test that '.' or '' relative_dir_path uses commit ref only (git ls-tree HEAD, not HEAD:.)."""
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git.ls_tree.return_value = "040000 tree abc123\t.github\n100644 blob def456\tREADME.md"

    list_directory_at_commit(".", "HEAD", repo_path="/tmp/repo")
    mock_repo.return_value.git.ls_tree.assert_called_once_with("HEAD")

    mock_repo.return_value.git.ls_tree.reset_mock()
    list_directory_at_commit("", "abc123", repo_path="/tmp/repo")
    mock_repo.return_value.git.ls_tree.assert_called_once_with("abc123")


def test_list_directory_at_commit_subdir_uses_rev_colon_path(mocker, mock_commits_availability):
    """Test that non-root relative_dir_path uses commit:path syntax."""
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git.ls_tree.return_value = "040000 tree x\tlampe\n"

    list_directory_at_commit("packages", "HEAD", repo_path="/tmp/repo")
    mock_repo.return_value.git.ls_tree.assert_called_once_with("HEAD:packages")


def test_list_directory_at_commit_formats_output(mocker, mock_commits_availability):
    """Test that ls_tree output is formatted as type, name, full_path per line in code block."""
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mocker.patch("lampe.core.tools.repository.content.sanitize_utf8", side_effect=lambda x: x)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git.ls_tree.return_value = (
        "040000 tree abc123\t.github\n" "100644 blob def456\tREADME.md\n" "100644 blob ghi789\tpyproject.toml"
    )

    result = list_directory_at_commit(".", "HEAD", repo_path="/tmp/repo")

    assert result == (
        "```\n" "tree\t.github\t.github\n" "blob\tREADME.md\tREADME.md\n" "blob\tpyproject.toml\tpyproject.toml\n" "```"
    )


def test_list_directory_at_commit_subdir_full_paths(mocker, mock_commits_availability):
    """Test that subdir listing builds correct full_path for each entry."""
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mocker.patch("lampe.core.tools.repository.content.sanitize_utf8", side_effect=lambda x: x)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git.ls_tree.return_value = "040000 tree x\tsrc\n" "100644 blob y\tmain.py"

    result = list_directory_at_commit("packages/lampe", "HEAD", repo_path="/tmp/repo")

    assert result == ("```\n" "tree\tsrc\tpackages/lampe/src\n" "blob\tmain.py\tpackages/lampe/main.py\n" "```")


def test_list_directory_at_commit_empty_directory(mocker, mock_commits_availability):
    """Test that empty ls_tree output returns 'Empty directory'."""
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git.ls_tree.return_value = ""

    result = list_directory_at_commit(".", "HEAD", repo_path="/tmp/repo")

    assert result == "Empty directory"


def test_list_directory_at_commit_empty_directory_whitespace_only(mocker, mock_commits_availability):
    """Test that whitespace-only ls_tree output returns 'Empty directory'."""
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git.ls_tree.return_value = "   \n\t  "

    result = list_directory_at_commit(".", "HEAD", repo_path="/tmp/repo")

    assert result == "Empty directory"


def test_list_directory_at_commit_path_not_found(mocker, mock_commits_availability):
    """Test that GitCommandError status 128 returns error message instead of raising."""
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git.ls_tree.side_effect = GitCommandError("ls-tree", status=128)

    result = list_directory_at_commit("nonexistent/dir", "HEAD", repo_path="/tmp/repo")

    assert "Error: Path not found or not a directory" in result


def test_list_directory_at_commit_generic_git_error(mocker, mock_commits_availability):
    """Test that other GitCommandError returns error string instead of raising."""
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git.ls_tree.side_effect = GitCommandError(
        "ls-tree", status=1, stderr="fatal: something went wrong"
    )

    result = list_directory_at_commit(".", "HEAD", repo_path="/tmp/repo")

    assert result.startswith("Error:")
    assert "something went wrong" in result or "Error" in result


def test_list_directory_at_commit_path_normalization_trailing_slash(mocker, mock_commits_availability):
    """Test that trailing slash is normalized (src/ uses HEAD:src)."""
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    mock_repo.return_value.git.ls_tree.return_value = "100644 blob x\tfile.py"

    list_directory_at_commit("src/", "HEAD", repo_path="/tmp/repo")

    mock_repo.return_value.git.ls_tree.assert_called_once_with("HEAD:src")


def test_list_directory_at_commit_applies_sanitize_utf8(mocker, mock_commits_availability):
    """Test that sanitize_utf8 is applied to ls_tree output."""
    mocker.patch("lampe.core.tools.repository.content.LocalCommitsAvailability", return_value=mock_commits_availability)
    sanitize_mock = mocker.patch("lampe.core.tools.repository.content.sanitize_utf8")
    mock_repo = mocker.patch("lampe.core.tools.repository.content.Repo")
    raw_output = "100644 blob x\tfile.py"
    mock_repo.return_value.git.ls_tree.return_value = raw_output
    sanitize_mock.return_value = "100644 blob x\tfile.py"

    list_directory_at_commit(".", "HEAD", repo_path="/tmp/repo")

    sanitize_mock.assert_called_once_with(raw_output)
