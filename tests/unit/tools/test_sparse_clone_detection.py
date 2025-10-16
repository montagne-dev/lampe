"""Tests for sparse clone detection functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from git import Repo

from lampe.core.tools.repository.management import is_sparse_clone


@pytest.fixture
def mock_repo():
    """Mock Git repository for testing."""
    mock_repo = Mock(spec=Repo)
    mock_repo.git = Mock()
    mock_repo.remotes.origin.url = "https://github.com/test/repo.git"

    with patch("lampe.core.tools.repository.management.Repo", return_value=mock_repo):
        yield mock_repo


@pytest.fixture
def tmp_path():
    """Temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


def test_is_sparse_clone_with_sparse_checkout_enabled(mock_repo):
    """Test detection when core.sparseCheckout is enabled."""
    # Mock the config to return "true" for sparse checkout
    mock_repo.git.config.side_effect = lambda key: "true" if key == "core.sparseCheckout" else ""

    result = is_sparse_clone("/fake/path")
    assert result is True


def test_is_sparse_clone_with_empty_sparse_checkout_file(mock_repo, tmp_path):
    """Test detection when .git/info/sparse-checkout file exists but is empty."""
    # Mock the config to not return sparse checkout
    mock_repo.git.config.side_effect = lambda key: ""

    # Create the sparse checkout file but empty
    sparse_file = tmp_path / ".git" / "info" / "sparse-checkout"
    sparse_file.parent.mkdir(parents=True)
    sparse_file.write_text("")

    with patch("lampe.core.tools.repository.management.Path") as mock_path:
        mock_path.return_value.__truediv__.return_value = sparse_file
        result = is_sparse_clone("/fake/path")
        assert result is False


def test_is_sparse_clone_with_shallow_and_sparse(mock_repo, tmp_path):
    """Test detection when shallow clone is combined with sparse checkout."""
    # Mock the config to return "true" for sparse checkout
    mock_repo.git.config.side_effect = lambda key: "true" if key == "core.sparseCheckout" else ""

    # Create shallow file
    shallow_file = tmp_path / ".git" / "shallow"
    shallow_file.parent.mkdir(parents=True)
    shallow_file.write_text("1234567890abcdef")

    with patch("lampe.core.tools.repository.management.Path") as mock_path:

        def path_side_effect(path):
            if path == "/fake/path":
                mock_path_obj = Mock()
                mock_path_obj.__truediv__.return_value = shallow_file
                return mock_path_obj
            return Mock()

        mock_path.side_effect = path_side_effect
        result = is_sparse_clone("/fake/path")
        assert result is True


def test_is_sparse_clone_no_indicators(mock_repo):
    """Test detection when no sparse clone indicators are present."""
    # Mock the config to not return sparse checkout
    mock_repo.git.config.side_effect = lambda key: ""

    # Mock fsck to succeed (no missing objects)
    mock_repo.git.fsck.return_value = ""

    result = is_sparse_clone("/fake/path")
    assert result is False


def test_is_sparse_clone_git_error(mock_repo):
    """Test detection when git commands fail."""
    # Mock the repo to raise an exception
    mock_repo.git.config.side_effect = Exception("Git error")

    result = is_sparse_clone("/fake/path")
    assert result is False
