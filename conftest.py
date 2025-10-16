import tempfile
from pathlib import Path
from typing import Callable

import pytest
from git import Repo


def create_commit(repo: Repo, message: str) -> str:
    """Create a commit and return its hash."""
    commit = repo.index.commit(message)
    return commit.hexsha


@pytest.fixture(scope="session")
def git_repo_with_branches() -> Callable[[str, str | None, str | None], tuple[str, str, str]]:
    """Create a temporary git repository with main and feature branches for testing.

    Parameters
    ----------
    file_path
        Path to the file within the repository
    base_content
        Content of the file in the base branch, None if file doesn't exist
    head_content
        Content of the file in the feature branch, None if file doesn't exist
    branch_name
        Name of the feature branch
    add_remote
        Whether to add a remote origin pointing to the repository itself (default: True)

    Returns
    -------
    Callable[[str, str | None, str | None], tuple[str, str, str]]
        A function that takes:
        - file_path: Path to the file within the repository
        - base_content: Content of the file in the base branch, None if file doesn't exist
        - head_content: Content of the file in the feature branch, None if file doesn't exist
        And returns a tuple containing:
        - repo_path: Path to the temporary git repository
        - base_commit_hash: Hash of the commit in main branch
        - head_commit_hash: Hash of the commit in feature branch
    """

    def _create_repo(
        file_path: str,
        base_content: str | None,
        head_content: str | None,
        branch_name: str = "feat/test-branch",
        add_remote: bool = True,
    ):
        temp_dir = tempfile.mkdtemp()
        repo = Repo.init(temp_dir)

        # Configure git user for commits
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        # Create main branch with base content
        repo.git.checkout("-b", "main")

        if base_content is not None:
            file_full_path = Path(temp_dir) / file_path
            file_full_path.parent.mkdir(parents=True, exist_ok=True)
            file_full_path.write_text(base_content)
            repo.index.add([file_path])
            base_commit_hash = create_commit(repo, "Initial commit with base content")
        else:
            # Create empty commit if file doesn't exist in base
            base_commit_hash = create_commit(repo, "Initial empty commit")

        # Create feature branch with head content (if different)
        if head_content is not None and head_content != base_content:
            repo.git.checkout("-b", branch_name)
            file_full_path = Path(temp_dir) / file_path
            file_full_path.parent.mkdir(parents=True, exist_ok=True)
            file_full_path.write_text(head_content)
            repo.index.add([file_path])
            head_commit_hash = create_commit(repo, "Feature commit with head content")
        elif head_content is None and base_content is not None:
            # Handle file deletion case
            repo.git.checkout("-b", branch_name)
            file_full_path = Path(temp_dir) / file_path
            if file_full_path.exists():
                file_full_path.unlink()
                repo.index.remove([file_path])
            head_commit_hash = create_commit(repo, "Delete file")
        else:
            head_commit_hash = base_commit_hash

        # Add remote origin pointing to the repository itself if requested
        if add_remote:
            repo.git.remote("add", "origin", temp_dir)

        return temp_dir, base_commit_hash, head_commit_hash

    return _create_repo
