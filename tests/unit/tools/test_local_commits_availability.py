from unittest.mock import Mock

from git import GitCommandError

from lampe.core.tools.repository import LocalCommitsAvailability


def test_local_commits_availability_init(mocker):
    """Test LocalCommitsAvailability initialization."""
    repo_path = "/path/to/repo"
    commits = ["abc123", "def456"]

    mock_repo_class = mocker.patch("lampe.core.tools.repository.management.Repo")
    mock_repo = Mock()
    mock_repo_class.return_value = mock_repo

    commits_availability = LocalCommitsAvailability(repo_path, commits)

    assert commits_availability.repo_path == repo_path
    assert commits_availability.commits == commits
    assert commits_availability._fetched_commits == []
    mock_repo_class.assert_called_once_with(path=repo_path)


def test_get_available_commits(mocker):
    """Test _get_available_commits method."""
    repo_path = "/path/to/repo"
    commits = ["abc123"]

    mock_repo = Mock()
    mock_repo.git.fsck.return_value = """Checking ref database: 100% (1/1), done.
Checking object directories: 100% (256/256), done.
root 71bc55741545ec0fc97cf393ba5a7a1b26d0f26e
root 5f3c4403176c8739f5be4e183d6de24372778e24
Checking objects: 100% (8237/8237), done.
dangling commit 5f3c4403176c8739f5be4e183d6de24372778e24"""

    mocker.patch("lampe.core.tools.repository.management.Repo", return_value=mock_repo)
    commits_availability = LocalCommitsAvailability(repo_path, commits)

    available_commits = commits_availability._get_available_commits()

    expected_commits = {"71bc55741545ec0fc97cf393ba5a7a1b26d0f26e", "5f3c4403176c8739f5be4e183d6de24372778e24"}
    assert available_commits == expected_commits
    mock_repo.git.fsck.assert_called_once_with("--root")


def test_context_manager_commits_already_available(mocker):
    """Test context manager when commits are already available."""
    repo_path = "/path/to/repo"
    commits = ["abc123"]

    mock_repo = Mock()
    mock_repo.git.fsck.return_value = "root abc123"
    mock_repo.rev_parse.return_value = "abc123"

    mocker.patch("lampe.core.tools.repository.management.Repo", return_value=mock_repo)
    mock_fetch = mocker.patch("lampe.core.tools.repository.management.fetch_commit_ref")
    with LocalCommitsAvailability(repo_path, commits) as commits_availability:
        assert commits_availability._fetched_commits == []

    # Should not call fetch_commit_ref since commit is already available
    mock_fetch.assert_not_called()


def test_context_manager_commits_not_available(mocker):
    """Test context manager when commits need to be fetched."""
    repo_path = "/path/to/repo"
    commits = ["abc123"]

    mock_repo = Mock()
    mock_repo.git.fsck.return_value = "root def456"
    mock_repo.rev_parse.return_value = "abc123"
    mock_repo.git.config.return_value = ("core.sparseCheckout", "true")
    mocker.patch("lampe.core.tools.repository.management.is_sparse_clone", return_value=True)
    mocker.patch("lampe.core.tools.repository.management.Repo", return_value=mock_repo)
    mock_fetch = mocker.patch("lampe.core.tools.repository.management.fetch_commit_ref")
    with LocalCommitsAvailability(repo_path, commits) as commits_availability:
        assert commits_availability._fetched_commits == ["abc123"]

    # Should call fetch_commit_ref since commit is not available
    mock_fetch.assert_called_once_with(repo_path, "abc123")


def test_context_manager_fetch_failure(mocker):
    """Test context manager when fetch fails."""
    repo_path = "/path/to/repo"
    commits = ["abc123"]

    mock_repo = Mock()
    mock_repo.git.fsck.return_value = "root def456"
    mock_repo.rev_parse.return_value = "abc123"

    mocker.patch("lampe.core.tools.repository.management.Repo", return_value=mock_repo)
    mocker.patch("lampe.core.tools.repository.management.fetch_commit_ref", side_effect=GitCommandError("Fetch failed"))
    mocker.patch("lampe.core.tools.repository.management.is_sparse_clone", return_value=True)
    mock_logger = mocker.patch("lampe.core.tools.repository.management.logger")
    with LocalCommitsAvailability(repo_path, commits) as commits_availability:
        assert commits_availability._fetched_commits == []

    # Should log a warning about the fetch failure
    mock_logger.warning.assert_called_once()


def test_context_manager_empty_commits_list(mocker):
    """Test context manager with empty commits list."""
    repo_path = "/path/to/repo"
    commits = []

    mocker.patch("lampe.core.tools.repository.management.Repo")
    with LocalCommitsAvailability(repo_path, commits) as commits_availability:
        assert commits_availability._fetched_commits == []
