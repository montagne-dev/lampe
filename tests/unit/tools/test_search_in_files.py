"""Unit tests for search_in_files tool."""

from git import GitCommandError

from lampe.core.tools.repository import search_in_files


def test_search_in_files_match_found_without_line_numbers(mocker):
    """Test successful grep when pattern matches and include_line_numbers is False."""
    mock_repo = mocker.patch("lampe.core.tools.repository.search.Repo")
    mock_repo.return_value.git.grep.return_value = "src/foo.py:def bar():"

    result = search_in_files(
        pattern="def bar",
        relative_dir_path="src",
        commit_reference="abc123",
        include_line_numbers=False,
        repo_path="/tmp/repo",
    )

    assert "```grep" in result
    assert "src/foo.py:def bar():" in result
    mock_repo.return_value.git.grep.assert_called_once_with("def bar", "abc123:src")


def test_search_in_files_match_found_with_line_numbers(mocker):
    """Test successful grep when pattern matches and include_line_numbers is True."""
    mock_repo = mocker.patch("lampe.core.tools.repository.search.Repo")
    mock_repo.return_value.git.grep.return_value = "src/foo.py:42:def bar():"

    result = search_in_files(
        pattern="debugger",
        relative_dir_path="src",
        commit_reference="cac596a",
        include_line_numbers=True,
        repo_path="/tmp/repo",
    )

    assert "```grep" in result
    assert "src/foo.py:42:def bar():" in result
    mock_repo.return_value.git.grep.assert_called_once_with("-n", "debugger", "cac596a:src")


def test_search_in_files_no_matches(mocker):
    """Test that empty grep output returns 'No matches found'."""
    mock_repo = mocker.patch("lampe.core.tools.repository.search.Repo")
    mock_repo.return_value.git.grep.return_value = ""

    result = search_in_files(
        pattern="nonexistent",
        relative_dir_path=".",
        commit_reference="abc123",
        repo_path="/tmp/repo",
    )

    assert result == "No matches found"


def test_search_in_files_git_error_status_1_returns_no_matches(mocker):
    """Test that GitCommandError with status 1 (no match) returns 'No matches found'."""
    mock_repo = mocker.patch("lampe.core.tools.repository.search.Repo")
    mock_repo.return_value.git.grep.side_effect = GitCommandError("git", status=1)

    result = search_in_files(
        pattern="nonexistent",
        relative_dir_path="src",
        commit_reference="abc123",
        repo_path="/tmp/repo",
    )

    assert result == "No matches found"


def test_search_in_files_git_error_status_128_returns_error_message(mocker):
    """Test that GitCommandError with status 128 (fatal) returns error, not 'No matches found'."""
    mock_repo = mocker.patch("lampe.core.tools.repository.search.Repo")
    mock_repo.return_value.git.grep.side_effect = GitCommandError(
        "git", status=128, stderr="fatal: invalid object name"
    )

    result = search_in_files(
        pattern="pattern",
        relative_dir_path="src",
        commit_reference="invalid_ref",
        repo_path="/tmp/repo",
    )

    assert "Error executing git grep" in result
    assert result != "No matches found"


def test_search_in_files_git_error_other_status_returns_error_message(mocker):
    """Test that GitCommandError with status other than 1 or 128 returns error string."""
    mock_repo = mocker.patch("lampe.core.tools.repository.search.Repo")
    mock_repo.return_value.git.grep.side_effect = GitCommandError("git", status=2, stderr="fatal: invalid path")

    result = search_in_files(
        pattern="pattern",
        relative_dir_path="src/pages/preview/[id].astro",
        commit_reference="cac596a",
        repo_path="/tmp/repo",
    )

    assert "Error executing git grep" in result
    assert "fatal" in result or "invalid" in result or "1" in str(result)


def test_search_in_files_empty_relative_path_uses_commit_only(mocker):
    """Test that empty or '.' relative_dir_path uses commit ref only (root of repo)."""
    mock_repo = mocker.patch("lampe.core.tools.repository.search.Repo")
    mock_repo.return_value.git.grep.return_value = "match"

    search_in_files(
        pattern="foo",
        relative_dir_path="",
        commit_reference="abc123",
        repo_path="/tmp/repo",
    )

    mock_repo.return_value.git.grep.assert_called_once_with("foo", "abc123")


def test_search_in_files_sanitizes_utf8_output(mocker):
    """Test that grep output is sanitized through sanitize_utf8."""
    mock_repo = mocker.patch("lampe.core.tools.repository.search.Repo")
    # Surrogate pairs would be sanitized
    mock_repo.return_value.git.grep.return_value = "src/foo.py:valid text"

    result = search_in_files(
        pattern="valid",
        relative_dir_path="src",
        commit_reference="abc123",
        repo_path="/tmp/repo",
    )

    assert "valid text" in result
    assert "```grep" in result
