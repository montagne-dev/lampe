import logging

import pytest

from lampe.core.tools.repository.management import TempGitRepository, UnableToDeleteError


def test_temp_git_repository(mocker):
    mock_clone_repo = mocker.patch(
        "lampe.core.tools.repository.management.clone_repo", return_value="local/path/to/repo"
    )
    mock_rmtree = mocker.patch("lampe.core.tools.repository.management.shutil.rmtree")
    with TempGitRepository("https://some/repo/url.git") as repo:
        mock_clone_repo.assert_called_once_with(
            repo_url="https://some/repo/url.git",
            base_ref=None,
            head_ref=None,
            folder_name=None,
            sparse=True,
            shallow=True,
            blob_filter=True,
            remove_existing=True,
        )
        assert repo.path_to_local_repo == "local/path/to/repo"
        mock_rmtree.assert_not_called()

    mock_rmtree.assert_called_once_with("local/path/to/repo")


def test_temp_git_repository__delete_file_not_found(mocker, caplog):
    mock_clone_repo = mocker.patch(
        "lampe.core.tools.repository.management.clone_repo", return_value="local/path/to/repo"
    )
    mock_rmtree = mocker.patch("lampe.core.tools.repository.management.shutil.rmtree", side_effect=FileNotFoundError)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(UnableToDeleteError):
            with TempGitRepository("https://some/repo/url.git") as repo:
                mock_clone_repo.assert_called_once_with(
                    repo_url="https://some/repo/url.git",
                    head_ref=None,
                    folder_name=None,
                    sparse=True,
                    shallow=True,
                    blob_filter=True,
                    remove_existing=True,
                )
                assert repo.path_to_local_repo == "local/path/to/repo"
                mock_rmtree.assert_not_called()

        assert "does not exist" in caplog.text
        assert "local/path/to/repo" in caplog.text

    mock_rmtree.assert_called_once_with("local/path/to/repo")


def test_temp_git_repository__delete_any_other_exception(mocker, caplog):
    mock_clone_repo = mocker.patch(
        "lampe.core.tools.repository.management.clone_repo", return_value="local/path/to/repo"
    )
    mock_rmtree = mocker.patch(
        "lampe.core.tools.repository.management.shutil.rmtree", side_effect=Exception("some problem happened")
    )
    with caplog.at_level(logging.ERROR):
        with pytest.raises(UnableToDeleteError):
            with TempGitRepository("https://some/repo/url.git") as repo:
                mock_clone_repo.assert_called_once_with(
                    repo_url="https://some/repo/url.git",
                    head_ref=None,
                    folder_name=None,
                    sparse=True,
                    shallow=True,
                    blob_filter=True,
                    remove_existing=True,
                )
                assert repo.path_to_local_repo == "local/path/to/repo"
                mock_rmtree.assert_not_called()

        assert "local/path/to/repo" in caplog.text
        assert "some problem happened" in caplog.text

    mock_rmtree.assert_called_once_with("local/path/to/repo")
