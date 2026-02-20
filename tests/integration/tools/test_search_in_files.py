"""Integration tests for search_in_files tool with real git repository."""

from pathlib import Path

from git import Repo

from lampe.core.tools.repository import search_in_files


def test_search_in_files_finds_pattern_in_real_repo(git_repo_with_branches):
    """Test search_in_files finds pattern in a real git repository."""
    # Create repo with a file containing 'debugger'
    base_content = 'console.log("hello");'
    head_content = 'debugger;\nconsole.log("hello");'

    repo_path, base_commit, head_commit = git_repo_with_branches("src/app.js", base_content, head_content)

    result = search_in_files(
        pattern="debugger",
        relative_dir_path="src",
        commit_reference=head_commit,
        include_line_numbers=True,
        repo_path=repo_path,
    )

    assert result != "No matches found"
    assert "```grep" in result
    assert "app.js" in result
    assert "debugger" in result


def test_search_in_files_no_match_returns_no_matches_found(git_repo_with_branches):
    """Test search_in_files returns 'No matches found' when pattern has no match."""
    base_content = "const x = 1;"
    head_content = "const x = 2;"

    repo_path, _, head_commit = git_repo_with_branches("src/foo.js", base_content, head_content)

    result = search_in_files(
        pattern="nonexistent_pattern_xyz",
        relative_dir_path="src",
        commit_reference=head_commit,
        repo_path=repo_path,
    )

    assert result == "No matches found"


def test_search_in_files_with_multiple_files(git_repo_with_branches):
    """Test search_in_files across multiple files in a directory."""
    base_content = "def hello(): pass"
    head_content = "def hello(): pass"

    repo_path, _, head_commit = git_repo_with_branches("src/main.py", base_content, head_content)

    # Add another file with same pattern
    repo = Repo(path=repo_path)
    other_file = Path(repo_path) / "src" / "utils.py"
    other_file.write_text('def hello(): return "world"')
    repo.index.add(["src/utils.py"])
    head_commit = repo.index.commit("Add utils").hexsha

    result = search_in_files(
        pattern="def hello",
        relative_dir_path="src",
        commit_reference=head_commit,
        include_line_numbers=True,
        repo_path=repo_path,
    )

    assert "No matches found" != result
    assert "main.py" in result
    assert "utils.py" in result
