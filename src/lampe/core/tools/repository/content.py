import logging

from git import GitCommandError, Repo

from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.core.tools.repository.encoding import sanitize_utf8
from lampe.core.tools.repository.management import LocalCommitsAvailability

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)

MAX_FILE_SIZE_CHARS = 300_000


def file_exists(file_path: str, commit_hash: str = "HEAD", repo_path: str = "/tmp/") -> bool:
    """Check if a file exists in a specific commit.

    Parameters
    ----------
    file_path
        Path to the file within the repository
    commit_hash
        Commit reference to check (e.g., commit hash, branch name, tag). Defaults to "HEAD"
    repo_path
        Path to git repository, by default "/tmp/"

    Returns
    -------
    bool
        True if file exists in the commit, False otherwise

    Raises
    ------
    GitCommandError
        If there is an unexpected git error
    """
    try:
        repo = Repo(path=repo_path)
        with LocalCommitsAvailability(repo_path, [commit_hash]):
            repo.git.cat_file("-e", f"{commit_hash}:{file_path}")
        return True
    except GitCommandError as e:
        if e.status == 128:
            return False
        logger.exception(f"Unexpected error checking if file exists: {e}")
        raise


def get_file_content_at_commit(
    commit_hash: str,
    file_path: str,
    line_start: int | None = None,
    line_end: int | None = None,
    include_line_numbers: bool = False,
    repo_path: str = "/tmp/",
) -> str:
    """Get file content from a specific commit.

    Parameters
    ----------
    commit_hash
        Commit reference (e.g., "main", commit hash)
    file_path
        Path to the file within the repository
    line_start
        Line range start index (0-based) of head_content to extract content from
    line_end
        Line range end index (0-based) of head_content to extract content to
    include_line_numbers
        Whether to prefix each line with its line number (default: False)
    repo_path
        Path to the git repository, by default "/tmp/"

    Returns
    -------
    :
        File content as a string, empty string if file doesn't exist or line range is invalid

    Raises
    ------
    GitCommandError
        If the file doesn't exist or any other git error occurs
    """
    try:
        # Check file size if no line range is specified
        if line_start is None and line_end is None:
            file_size = get_file_size_at_commit(file_path, commit_hash, repo_path)
            if file_size > MAX_FILE_SIZE_CHARS:
                error_msg = (
                    f"Error: File too large (>{MAX_FILE_SIZE_CHARS // 1000}KB). File size: {file_size} bytes. "
                    "Cannot read full file content. "
                    "Please use line_start and line_end parameters to read specific line ranges."
                )
                logger.warning(f"File {file_path} at {commit_hash} is too large ({file_size} bytes)")
                return error_msg

        blob = ""
        repo = Repo(path=repo_path)
        with LocalCommitsAvailability(repo_path, [commit_hash]):
            blob = repo.git.show(f"{commit_hash}:{file_path}")
            blob = sanitize_utf8(blob)
        if line_start is not None and line_end is not None:
            blob = "\n".join(blob.splitlines()[line_start : line_end + 1])

        if include_line_numbers:
            lines = blob.splitlines()
            numbered_lines = []
            start_line = 0 if line_start is None else line_start
            for i, line in enumerate(lines):
                line_number = start_line + i
                numbered_lines.append(f"{line_number:>6}| {line}")
            blob = "\n".join(numbered_lines)

        return blob
    except GitCommandError as e:
        logger.exception(f"Error getting file content: {e}")
        raise


def list_directory_at_commit(
    relative_dir_path: str,
    commit_hash: str = "HEAD",
    repo_path: str = "/tmp/",
) -> str:
    """List directory contents at a specific commit (like ls).

    Parameters
    ----------
    relative_dir_path
        Directory path relative to repository root (e.g. "src/", "." for repo root)
    commit_hash
        Commit reference to list at (e.g., "main", commit hash). Defaults to "HEAD"
    repo_path
        Path to the git repository, by default "/tmp/"

    Returns
    -------
    str
        Formatted listing of entries: type (blob/tree), name, path. One per line.
    """
    try:
        repo = Repo(path=repo_path)
        with LocalCommitsAvailability(repo_path, [commit_hash]):
            tree_ref = f"{commit_hash}:{relative_dir_path.rstrip('/') or '.'}"
            ls_output = repo.git.ls_tree(tree_ref)
            ls_output = sanitize_utf8(ls_output)
        if not ls_output.strip():
            return "Empty directory"
        lines = []
        for line in ls_output.splitlines():
            # Format: <mode> <type> <hash><tab><name>
            parts = line.split("\t", 1)
            if len(parts) == 2:
                header, name = parts
                obj_type = header.split()[1] if len(header.split()) >= 2 else "?"
                prefix = relative_dir_path.rstrip("/") or "."
                full_path = f"{prefix}/{name}" if prefix != "." else name
                lines.append(f"{obj_type}\t{name}\t{full_path}")
            else:
                lines.append(line)
        return "```\n" + "\n".join(lines) + "\n```"
    except GitCommandError as e:
        if e.status == 128:
            return f"Error: Path not found or not a directory at {commit_hash}"
        logger.exception(f"Error listing directory: {e}")
        return f"Error: {str(e)}"


def get_file_size_at_commit(file_path: str, commit_hash: str = "HEAD", repo_path: str = "/tmp/") -> int:
    """Get the size of a file at a specific commit.

    Parameters
    ----------
    file_path
        Path to the file within the repository
    commit_hash
        Commit reference (e.g., "main", commit hash). Defaults to "HEAD"
    repo_path
        Path to the git repository, by default "/tmp/"

    Returns
    -------
    :
        Size of the file in bytes
    """
    repo = Repo(path=repo_path)
    with LocalCommitsAvailability(repo_path, [commit_hash]):
        tree = repo.commit(rev=commit_hash).tree
    try:
        git_obj = tree[file_path]
        return git_obj.size
    except KeyError:
        return 0
