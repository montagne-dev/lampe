from unittest.mock import MagicMock, patch

import pytest

from lampe.core.tools.repository import clone_repo, fetch_commit_ref


@pytest.fixture
def mock_repo():
    with patch("lampe.core.tools.repository.management.Repo") as mock:
        mock_instance = MagicMock()
        mock_instance.git_dir = "/tmp/test_repo/.git"
        mock.clone_from.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_git_version_check():
    with patch("lampe.core.tools.repository.management.valid_git_version_available") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_fetch_commit_ref():
    with patch("lampe.core.tools.repository.management.fetch_commit_ref") as mock:
        yield mock


@pytest.fixture
def mock_os_path_exists():
    with patch("os.path.exists") as mock:
        mock.return_value = False
        yield mock


def test_fetch_commit_ref(mocker):
    mock_repo = MagicMock()
    repo_path = "/tmp/test_repo"
    commit_ref = "main"

    mock_repo_class = mocker.patch("lampe.core.tools.repository.management.Repo", return_value=mock_repo)

    fetch_commit_ref(repo_path, commit_ref)

    mock_repo_class.assert_called_once_with(path=repo_path)
    mock_repo.git.fetch.assert_called_once_with("--no-tags", "--depth=1", "--filter=blob:none", "origin", commit_ref)


def test_fetch_commit_ref_error(mocker):
    from git import GitCommandError

    mock_repo = MagicMock()
    repo_path = "/tmp/test_repo"
    commit_ref = "main"
    mock_repo.git.fetch.side_effect = GitCommandError("fetch", "Fetch failed")

    mock_repo_class = mocker.patch("lampe.core.tools.repository.management.Repo", return_value=mock_repo)

    with pytest.raises(GitCommandError):
        fetch_commit_ref(repo_path, commit_ref)

    mock_repo_class.assert_called_once_with(path=repo_path)
    mock_repo.git.fetch.assert_called_once_with("--no-tags", "--depth=1", "--filter=blob:none", "origin", commit_ref)


def test_clone_basic(mock_repo, mock_git_version_check):
    repo_url = "https://github.com/test/repo.git"
    result = clone_repo(repo_url)

    mock_git_version_check.assert_called_once()
    mock_repo.clone_from.assert_called_once()

    # Check that multi_options contains the default flags
    call_args = mock_repo.clone_from.call_args
    assert call_args[0][0] == repo_url  # First positional arg is repo_url
    assert "multi_options" in call_args[1]
    multi_options = call_args[1]["multi_options"]
    assert "--depth" in multi_options and "1" in multi_options
    assert "--sparse" in multi_options
    assert "--filter" in multi_options and "blob:none" in multi_options

    assert result == "/tmp/test_repo"


def test_clone_with_custom_name(mock_repo, mock_git_version_check):
    repo_url = "https://github.com/test/repo.git"
    folder_name = "custom_name"

    result = clone_repo(repo_url, folder_name=folder_name)

    mock_git_version_check.assert_called_once()
    mock_repo.clone_from.assert_called_once()

    call_args = mock_repo.clone_from.call_args
    assert repo_url == call_args[0][0]
    assert folder_name in call_args[0][1]  # folder_name should be in the path
    assert result == "/tmp/test_repo"


def test_clone_shallow_disabled(mock_repo, mock_git_version_check):
    repo_url = "https://github.com/test/repo.git"

    result = clone_repo(repo_url, shallow=False)

    mock_git_version_check.assert_called_once()
    mock_repo.clone_from.assert_called_once()

    call_args = mock_repo.clone_from.call_args
    multi_options = call_args[1]["multi_options"]
    assert "--depth" not in multi_options
    assert result == "/tmp/test_repo"


def test_clone_sparse_disabled(mock_repo, mock_git_version_check):
    repo_url = "https://github.com/test/repo.git"

    result = clone_repo(repo_url, sparse=False)

    mock_git_version_check.assert_called_once()
    mock_repo.clone_from.assert_called_once()

    call_args = mock_repo.clone_from.call_args
    multi_options = call_args[1]["multi_options"]
    assert "--sparse" not in multi_options
    assert result == "/tmp/test_repo"


def test_clone_blob_filter_disabled(mock_repo, mock_git_version_check):
    repo_url = "https://github.com/test/repo.git"

    result = clone_repo(repo_url, blob_filter=False)

    mock_git_version_check.assert_called_once()
    mock_repo.clone_from.assert_called_once()

    call_args = mock_repo.clone_from.call_args
    multi_options = call_args[1]["multi_options"]
    assert "--filter" not in multi_options
    assert result == "/tmp/test_repo"


def test_clone_with_head_ref(mock_repo, mock_git_version_check):
    repo_url = "https://github.com/test/repo.git"
    head_ref = "feature-branch"

    result = clone_repo(repo_url, head_ref=head_ref)

    mock_git_version_check.assert_called_once()
    mock_repo.clone_from.assert_called_once()

    call_args = mock_repo.clone_from.call_args
    multi_options = call_args[1]["multi_options"]
    assert "--revision" in multi_options
    assert head_ref in multi_options
    assert result == "/tmp/test_repo"


def test_clone_with_all_options_disabled(mock_repo, mock_git_version_check):
    repo_url = "https://github.com/test/repo.git"

    result = clone_repo(repo_url, sparse=False, shallow=False, blob_filter=False)

    mock_git_version_check.assert_called_once()
    mock_repo.clone_from.assert_called_once()

    call_args = mock_repo.clone_from.call_args
    multi_options = call_args[1]["multi_options"]
    assert "--depth" not in multi_options
    assert "--sparse" not in multi_options
    assert "--filter" not in multi_options
    assert result == "/tmp/test_repo"


def test_clone_existing_directory_removed(mock_repo, mock_git_version_check):
    repo_url = "https://github.com/test/repo.git"

    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("shutil.rmtree") as mock_rmtree:
            result = clone_repo(repo_url)

            mock_git_version_check.assert_called_once()
            mock_rmtree.assert_called_once()
            mock_repo.clone_from.assert_called_once()
            assert result == "/tmp/test_repo"


def test_clone_existing_directory_no_remove(mock_repo, mock_git_version_check):
    repo_url = "https://github.com/test/repo.git"

    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("shutil.rmtree") as mock_rmtree:
            with patch("lampe.core.tools.repository.management.mkdtemp") as mock_mkdtemp:
                mock_mkdtemp.return_value = "/tmp/existing_dir"

                result = clone_repo(repo_url, remove_existing=False)

                mock_git_version_check.assert_called_once()
                mock_rmtree.assert_not_called()
                mock_repo.clone_from.assert_not_called()
                assert result == "/tmp/existing_dir"


def test_clone_git_version_check_fails(mock_repo):
    repo_url = "https://github.com/test/repo.git"

    with patch("lampe.core.tools.repository.management.valid_git_version_available") as mock_git_version_check:
        mock_git_version_check.return_value = False

        with pytest.raises(RuntimeError, match="Git version check failed"):
            clone_repo(repo_url)

        mock_git_version_check.assert_called_once()
        mock_repo.clone_from.assert_not_called()


def test_clone_error(mock_repo, mock_git_version_check):
    from git import GitCommandError

    repo_url = "https://github.com/test/repo.git"
    mock_repo.clone_from.side_effect = GitCommandError("clone", "Clone failed")

    with pytest.raises(GitCommandError):
        clone_repo(repo_url)

    mock_git_version_check.assert_called_once()
    mock_repo.clone_from.assert_called_once()


def test_clone_with_base_ref(mock_repo, mock_git_version_check, mock_fetch_commit_ref):
    repo_url = "https://github.com/test/repo.git"
    base_ref = "main"

    result = clone_repo(repo_url, base_ref=base_ref)

    mock_git_version_check.assert_called_once()
    mock_repo.clone_from.assert_called_once()
    mock_fetch_commit_ref.assert_called_once_with(result, base_ref)

    assert result == "/tmp/test_repo"


def test_clone_with_head_ref_and_base_ref(mock_repo, mock_git_version_check, mock_fetch_commit_ref):
    repo_url = "https://github.com/test/repo.git"
    head_ref = "feature-branch"
    base_ref = "main"

    result = clone_repo(repo_url, head_ref=head_ref, base_ref=base_ref)

    mock_git_version_check.assert_called_once()
    mock_repo.clone_from.assert_called_once()

    call_args = mock_repo.clone_from.call_args
    multi_options = call_args[1]["multi_options"]
    assert "--revision" in multi_options
    assert head_ref in multi_options

    mock_fetch_commit_ref.assert_called_once_with(result, base_ref)

    assert result == "/tmp/test_repo"


def test_clone_without_base_ref_no_fetch(mock_repo, mock_git_version_check, mock_fetch_commit_ref):
    repo_url = "https://github.com/test/repo.git"

    result = clone_repo(repo_url)

    mock_git_version_check.assert_called_once()
    mock_repo.clone_from.assert_called_once()

    mock_fetch_commit_ref.assert_not_called()

    assert result == "/tmp/test_repo"
