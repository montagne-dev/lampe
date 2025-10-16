from unittest.mock import MagicMock

import pytest

from lampe.core.tools.repository import get_diff_between_commits


@pytest.fixture
def mock_commits_availability():
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_context)
    mock_context.__exit__ = MagicMock(return_value=None)
    return mock_context


def make_mock_repo(mocker, files, diffs):
    """Create a mock Git repository with configurable file list and diffs."""
    mock_repo = mocker.patch("lampe.core.tools.repository.diff.Repo")
    mock_git = mock_repo.return_value.git

    def mock_diff_side_effect(*args, **kwargs):
        """Mock git diff behavior for both --name-only and actual diff calls."""
        if "--name-only" in args:
            return "\n".join(files)

        # Handle actual diff calls with file arguments after "--"
        if "--" in args:
            separator_index = args.index("--")
            file_args = args[separator_index + 1 :]
        else:
            # Fallback for single file argument
            file_args = [args[-1]]

        # Combine diffs for all requested files
        requested_diffs = [diffs[file_path] for file_path in file_args if file_path in diffs]
        return "\n".join(requested_diffs)

    mock_git.diff.side_effect = mock_diff_side_effect
    return mock_repo


def test_get_diff_between_commits_include_patterns(mocker, mock_commits_availability):
    files = ["a.py", "b.txt", "c.py"]
    diffs = {"a.py": "diff a", "b.txt": "diff b", "c.py": "diff c"}
    make_mock_repo(mocker, files, diffs)
    mocker.patch("lampe.core.tools.repository.diff.LocalCommitsAvailability", return_value=mock_commits_availability)
    repo_path = "/fake/path"
    base = "abc123"
    head = "def456"
    result = get_diff_between_commits(base, head, files_include_patterns=["*.py"], repo_path=repo_path)
    assert "diff a" in result
    assert "diff c" in result
    assert "diff b" not in result


def test_get_diff_between_commits_exclude_patterns(mocker, mock_commits_availability):
    files = ["a.py", "b.txt", "c.py"]
    diffs = {"a.py": "diff a", "b.txt": "diff b", "c.py": "diff c"}
    make_mock_repo(mocker, files, diffs)
    mocker.patch("lampe.core.tools.repository.diff.LocalCommitsAvailability", return_value=mock_commits_availability)
    repo_path = "/fake/path"
    base = "abc123"
    head = "def456"
    result = get_diff_between_commits(base, head, files_exclude_patterns=["*.txt"], repo_path=repo_path)
    assert "diff a" in result
    assert "diff c" in result
    assert "diff b" not in result


def test_get_diff_between_commits_include_and_exclude_patterns(mocker, mock_commits_availability):
    files = ["a.py", "b.txt", "c.py", "d.md"]
    diffs = {"a.py": "diff a", "b.txt": "diff b", "c.py": "diff c", "d.md": "diff d"}
    make_mock_repo(mocker, files, diffs)
    mocker.patch("lampe.core.tools.repository.diff.LocalCommitsAvailability", return_value=mock_commits_availability)
    repo_path = "/fake/path"
    base = "abc123"
    head = "def456"
    result = get_diff_between_commits(
        base,
        head,
        files_include_patterns=["*.py", "*.md"],
        files_exclude_patterns=["d.md"],
        repo_path=repo_path,
    )
    assert "diff a" in result
    assert "diff c" in result
    assert "diff d" not in result
    assert "diff b" not in result


def test_get_diff_between_commits_reinclude_patterns(mocker, mock_commits_availability):
    files = ["a.py", "b.txt", "c.py", "d.md"]
    diffs = {"a.py": "diff a", "b.txt": "diff b", "c.py": "diff c", "d.md": "diff d"}
    make_mock_repo(mocker, files, diffs)
    mocker.patch("lampe.core.tools.repository.diff.LocalCommitsAvailability", return_value=mock_commits_availability)
    repo_path = "/fake/path"
    base = "abc123"
    head = "def456"
    result = get_diff_between_commits(
        base,
        head,
        files_include_patterns=["*.py", "*.md", "*.txt"],
        files_exclude_patterns=["*.md", "*.txt"],
        repo_path=repo_path,
        files_reinclude_patterns=["d.md"],
    )
    assert "diff a" in result
    assert "diff c" in result
    assert "diff d" in result  # re-included
    assert "diff b" not in result


def test_get_diff_between_commits_all_patterns_none(mocker, mock_commits_availability):
    files = ["a.py", "b.txt"]
    diffs = {"a.py": "diff a", "b.txt": "diff b"}
    make_mock_repo(mocker, files, diffs)
    mocker.patch("lampe.core.tools.repository.diff.LocalCommitsAvailability", return_value=mock_commits_availability)
    repo_path = "/fake/path"
    base = "abc123"
    head = "def456"
    result = get_diff_between_commits(base, head, repo_path=repo_path)
    assert "diff a" in result
    assert "diff b" in result


def test_get_diff_between_commits_all_files_excluded(mocker, mock_commits_availability):
    files = ["a.py", "b.txt"]
    diffs = {"a.py": "diff a", "b.txt": "diff b"}
    make_mock_repo(mocker, files, diffs)
    mocker.patch("lampe.core.tools.repository.diff.LocalCommitsAvailability", return_value=mock_commits_availability)
    repo_path = "/fake/path"
    base = "abc123"
    head = "def456"
    result = get_diff_between_commits(base, head, files_exclude_patterns=["*"], repo_path=repo_path)
    assert result.strip() == ""


def test_get_diff_between_commits_all_files_reincluded(mocker, mock_commits_availability):
    files = ["a.py", "b.txt"]
    diffs = {"a.py": "diff a", "b.txt": "diff b"}
    make_mock_repo(mocker, files, diffs)
    mocker.patch("lampe.core.tools.repository.diff.LocalCommitsAvailability", return_value=mock_commits_availability)
    repo_path = "/fake/path"
    base = "abc123"
    head = "def456"
    result = get_diff_between_commits(
        base,
        head,
        files_exclude_patterns=["*"],
        files_reinclude_patterns=["a.py", "b.txt"],
        repo_path=repo_path,
    )
    assert "diff a" in result
    assert "diff b" in result


def test_get_diff_between_commits_overlapping_patterns_warning(mocker, caplog, mock_commits_availability):
    files = ["a.py", "b.txt"]
    diffs = {"a.py": "diff a", "b.txt": "diff b"}
    make_mock_repo(mocker, files, diffs)
    mocker.patch("lampe.core.tools.repository.diff.LocalCommitsAvailability", return_value=mock_commits_availability)
    repo_path = "/fake/path"
    base = "abc123"
    head = "def456"
    result = get_diff_between_commits(
        base,
        head,
        files_include_patterns=["*.py", "*.txt"],
        files_exclude_patterns=["*.txt"],
        repo_path=repo_path,
    )
    assert "diff a" in result
    assert "diff b" not in result
    assert "Overlapping patterns found in include and exclude patterns: {'*.txt'}" in caplog.text
    assert "Exclude patterns will take precedence as per git pathspec documentation" in caplog.text
