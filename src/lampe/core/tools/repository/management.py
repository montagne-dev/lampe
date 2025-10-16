import logging
import os
import shutil
import uuid
from pathlib import Path
from tempfile import mkdtemp

from git import GitCommandError, Repo

from lampe.core.gitconfig import valid_git_version_available
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.core.tools.repository.exceptions import UnableToDeleteError

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)


def _repo_to_path(repo: Repo) -> str:
    return str(Path(repo.git_dir).parent)


class TempGitRepository:
    """Context Manager for cloning and cleaning up a local clone of a repository

    Uses partial clone optimizations including shallow clone, sparse checkout, and blob filtering
    to efficiently fetch only required content. Upon exit, will attempt to delete the cloned repository.

    Attributes
    ----------
    repo_url
        Repository URL to clone
    head_ref
        Optional head ref to check out.
    folder_name
        Optional name prefix for temp directory
    sparse
        Enable sparse checkout mode to avoid populating all files initially.
    shallow
        Enable shallow clone (depth=1) to fetch only the target commit.
    blob_filter
        Enable blob filtering (--filter=blob:none) to fetch file contents on-demand
    remove_existing
        Remove existing directory if it exists

    Raises
    ------
    RuntimeError
        If Git version check fails
    GitCommandError
        If clone operation fails
    UnableToDeleteError
        If unable to delete the cloned repository
    """

    def __init__(
        self,
        repo_url: str,
        head_ref: str | None = None,
        base_ref: str | None = None,
        folder_name: str | None = None,
        sparse: bool = True,
        shallow: bool = True,
        blob_filter: bool = True,
        remove_existing: bool = True,
    ):
        self.repo_url = repo_url
        self.head_ref = head_ref
        self.base_ref = base_ref
        self.folder_name = folder_name
        self.sparse = sparse
        self.shallow = shallow
        self.blob_filter = blob_filter
        self.remove_existing = remove_existing
        self.path_to_local_repo = None

    def __enter__(self):
        self.path_to_local_repo = clone_repo(
            repo_url=self.repo_url,
            head_ref=self.head_ref,
            base_ref=self.base_ref,
            folder_name=self.folder_name,
            sparse=self.sparse,
            shallow=self.shallow,
            blob_filter=self.blob_filter,
            remove_existing=self.remove_existing,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.path_to_local_repo:
            try:
                shutil.rmtree(self.path_to_local_repo)
            except FileNotFoundError as e:
                logger.exception(f"Failed to delete {self.path_to_local_repo} because it does not exist.")
                raise UnableToDeleteError(self.path_to_local_repo) from e
            except Exception as e:
                logger.exception(f"Unable to delete local repo at path {self.path_to_local_repo}: {str(e)}")
                raise UnableToDeleteError(self.path_to_local_repo) from e


def clone_repo(
    repo_url: str,
    head_ref: str | None = None,
    base_ref: str | None = None,
    folder_name: str | None = None,
    sparse: bool = True,
    shallow: bool = True,
    blob_filter: bool = True,
    remove_existing: bool = True,
) -> str:
    """Clone a repository optimized for PR review.

    Uses partial clone optimizations including shallow clone, sparse checkout, and blob filtering
    to efficiently fetch only required content.

    Parameters
    ----------
    repo_url
        Repository URL to clone
    head_ref
        Head ref to checkout
    base_ref
        Base ref to fetch for diff computation
    folder_name
        Optional name prefix for temp directory
    sparse
        Enable sparse checkout mode to avoid populating all files initially
    shallow
        Enable shallow clone (depth=1) to fetch only the target commit
    blob_filter
        Enable blob filtering (--filter=blob:none) to fetch file contents on-demand
    remove_existing
        Remove existing directory if it exists

    Returns
    -------
    :
        Path to the cloned repository

    Raises
    ------
    RuntimeError
        If Git version check fails
    GitCommandError
        If clone operation fails
    """
    if not valid_git_version_available():
        raise RuntimeError("Git version check failed. Please upgrade Git to the minimum required version.")

    tmp_dir = f"/tmp/{folder_name}" if folder_name else mkdtemp(prefix=str(uuid.uuid4()))
    logger.info(f"Cloning repo (sparse={sparse}, shallow={shallow}, blob_filter={blob_filter}) to {tmp_dir}")

    if os.path.exists(tmp_dir):
        if remove_existing:
            logger.info(f"Removing existing directory {tmp_dir}")
            shutil.rmtree(tmp_dir)
        else:
            return tmp_dir

    clone_args = []
    if shallow:
        clone_args.extend(["--depth", "1"])
    if sparse:
        clone_args.append("--sparse")
    if blob_filter:
        clone_args.extend(["--filter", "blob:none"])
    if head_ref:
        clone_args.extend(["--revision", head_ref])

    try:
        repository_path = ""
        repo = Repo.clone_from(repo_url, tmp_dir, multi_options=clone_args)
        repository_path = _repo_to_path(repo)
        if sparse and blob_filter:
            logger.info("Partial clone ready - file contents will be fetched on-demand during git operations")
        if base_ref:
            fetch_commit_ref(repository_path, base_ref)
    except GitCommandError as e:
        logger.exception(f"Clone failed: {e}\nClone arguments used: {clone_args}")
        raise e

    return repository_path


def fetch_commit_ref(repo_path: str, commit_ref: str) -> None:
    """Fetch a base reference from the remote repository.

    Parameters
    ----------
    repo_path
        Path to the git repository
    commit_ref
        Commit reference to fetch (e.g., branch name, commit hash)

    Raises
    ------
    GitCommandError
        If the fetch operation fails
    """
    repo = Repo(path=repo_path)

    repo.git.fetch("--no-tags", "--depth=1", "--filter=blob:none", "origin", commit_ref)


class LocalCommitsAvailability:
    """Context manager to check if commits are available locally before git operations.

    Checks if specified commits exist locally using `git fsck --root` and fetches
    them if they're not present. This is useful for ensuring all required commits
    are available before performing git operations that depend on them.

    Attributes
    ----------
    repo_path
        Path to the git repository
    commits
        List of commit references to check and fetch if needed
    """

    def __init__(self, repo_path: str, commits: list[str]):
        self.repo_path = repo_path
        self.commits = commits
        self.repo = Repo(path=repo_path)
        self._fetched_commits = []

    def _get_available_commits(self) -> set[str]:
        fsck_output = ""

        fsck_output = self.repo.git.fsck("--root")

        available_commits = set()
        for line in fsck_output.splitlines():
            if line.startswith("root "):
                # Extract commit hash from lines like "root 71bc55741545ec0fc97cf393ba5a7a1b26d0f26e"
                parts = line.split()
                if len(parts) >= 2:
                    available_commits.add(parts[1])
            elif line.startswith("dangling commit "):
                # Extract commit hash from lines like "dangling commit 5f3c4403176c8739f5be4e183d6de24372778e24"
                parts = line.split()
                if len(parts) >= 3:
                    available_commits.add(parts[2])
        logger.debug(f"Available commits: {available_commits}")
        return available_commits

    def __enter__(self):
        if not self.commits:
            logger.debug("No commits to check")
            return self

        if not is_sparse_clone(self.repo_path):
            logger.warning("Repository is not a sparse clone, skipping commit checks")
            return self

        available_commits = self._get_available_commits()

        for commit in self.commits:
            if commit not in available_commits:
                logger.debug(f"Commit {commit} not found locally, fetching...")
                try:
                    fetch_commit_ref(self.repo_path, commit)
                    self._fetched_commits.append(commit)
                except GitCommandError as e:
                    logger.warning(f"Failed to fetch commit {commit} ({e}) continuing anyway")
            else:
                logger.debug(f"Commit {commit} found locally")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._fetched_commits:
            logger.debug(f"Fetched commits during context: {self._fetched_commits}")
        return False


def is_sparse_clone(repo_path: str) -> bool:
    """Check if a repository is a sparse clone.

    A sparse clone is detected by checking multiple indicators:
    1. If core.sparseCheckout is enabled
    2. If .git/info/sparse-checkout file exists and has content

    Parameters
    ----------
    repo_path
        Path to the git repository

    Returns
    -------
    bool
        True if the repository appears to be a sparse clone, False otherwise

    Raises
    ------
    GitCommandError
        If git commands fail
    """
    try:
        repo = Repo(path=repo_path)

        # Check if sparse checkout is enabled
        try:
            sparse_checkout = repo.git.config("core.sparseCheckout")
            if sparse_checkout.strip().lower() == "true":
                logger.debug(f"Sparse checkout enabled in {repo_path}")
                return True
        except GitCommandError:
            # core.sparseCheckout not set, continue with other checks
            pass

        # Check if .git/info/sparse-checkout file exists and has content
        sparse_checkout_file = Path(repo_path) / ".git" / "info" / "sparse-checkout"
        if sparse_checkout_file.exists():
            with open(sparse_checkout_file, "r") as f:
                content = f.read().strip()
                if content:
                    logger.debug(f"Sparse checkout file found with content in {repo_path}")
                    return True

        logger.debug(f"No sparse clone indicators found in {repo_path}")
        return False

    except Exception as e:
        logger.exception(f"Error checking if repository is sparse clone: {e}")
        return False
