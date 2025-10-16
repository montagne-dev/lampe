import tempfile
from pathlib import Path

from git import Repo

from lampe.core.tools.repository import LocalCommitsAvailability, get_file_content_at_commit


def test_local_commits_availability():
    """Test LocalCommitsAvailability when some commits are available and others need fetching."""
    # Create a temporary repository as the "remote"
    remote_dir = tempfile.mkdtemp()
    remote_repo = Repo.init(remote_dir)

    # Configure git user for commits
    remote_repo.config_writer().set_value("user", "name", "Test User").release()
    remote_repo.config_writer().set_value("user", "email", "test@example.com").release()

    # Create initial commit
    test_file = Path(remote_dir) / "test_file.txt"
    test_file.write_text("Initial content")
    remote_repo.index.add(["test_file.txt"])
    initial_commit = remote_repo.index.commit("Initial commit")

    # Create a second commit
    test_file.write_text("Modified content")
    remote_repo.index.add(["test_file.txt"])
    _ = remote_repo.index.commit("Second commit")

    # Create a third commit
    test_file.write_text("Final content")
    remote_repo.index.add(["test_file.txt"])
    third_commit = remote_repo.index.commit("Third commit")

    # Create a repo that has only the first commit
    partial_dir = tempfile.mkdtemp()
    partial_repo = Repo.init(partial_dir)
    partial_repo.config_writer().set_value("user", "name", "Test User").release()
    partial_repo.config_writer().set_value("user", "email", "test@example.com").release()

    # Add remote and fetch only the first commit
    partial_repo.git.remote("add", "origin", remote_dir)
    partial_repo.git.fetch("origin", initial_commit.hexsha)
    partial_repo.git.config("core.sparseCheckout", "true")

    # Test LocalCommitsAvailability with mixed available/missing commits
    with LocalCommitsAvailability(partial_dir, [initial_commit.hexsha, third_commit.hexsha]) as commits_availability:
        # Verify only the missing commit was fetched
        assert len(commits_availability._fetched_commits) == 1
        assert third_commit.hexsha in commits_availability._fetched_commits
        assert initial_commit.hexsha not in commits_availability._fetched_commits

        # Verify we can access both commits
        initial_content = get_file_content_at_commit(initial_commit.hexsha, "test_file.txt", repo_path=partial_dir)
        third_content = get_file_content_at_commit(third_commit.hexsha, "test_file.txt", repo_path=partial_dir)

        assert initial_content == "Initial content"
        assert third_content == "Final content"
