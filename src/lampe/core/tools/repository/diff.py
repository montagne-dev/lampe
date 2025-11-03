import logging
from fnmatch import fnmatch
from itertools import batched

from git import GitCommandError, Repo

from lampe.core.loggingconfig import LAMPE_LOGGER_NAME
from lampe.core.tools.repository.content import get_file_size_at_commit
from lampe.core.tools.repository.exceptions import DiffNotFoundError
from lampe.core.tools.repository.management import LocalCommitsAvailability

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)


def list_changed_files(base_reference: str, head_reference: str = "HEAD", repo_path: str = "/tmp/") -> str:
    """List files changed between base reference and HEAD, with change stats.

    Parameters
    ----------
    base_reference
        Git reference (commit hash, branch name, etc.) to compare against HEAD
    head_reference
        Git reference (commit hash, branch name, etc.) to compare against base reference. Defaults to "HEAD"
    repo_path
        Path to git repository, by default "/tmp/"

    Returns
    -------
    str
        Formatted string listing changed files with status, additions/deletions and size
        Format: "[STATUS] filepath | +additions -deletions | sizeKB"
        STATUS is one of: A (added), D (deleted), M (modified)

    Raises
    ------
    GitCommandError
        If there is an error executing git commands
    """
    repo = Repo(path=repo_path)
    numstat = repo.git.diff(base_reference, "--numstat")
    status_output = repo.git.diff(base_reference, "--name-status")

    status_map = {}
    for line in status_output.splitlines():
        if line:
            parts = line.split("\t")
            if len(parts) >= 2:
                status, path = parts[0], parts[-1]
                status_map[path] = "A" if status == "A" else "D" if status == "D" else "M"

    result = []
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            additions, deletions, file_path = parts
            try:
                additions = int(additions)
            except ValueError:
                additions = 0
            try:
                deletions = int(deletions)
            except ValueError:
                deletions = 0
            try:
                size_kb = get_file_size_at_commit(file_path, head_reference, repo_path)
            except GitCommandError as e:
                size_kb = 0
                logger.exception(f"During list_changed_files, error getting file size: {e}, continuing...")

            status = status_map.get(file_path, "M")

            result.append(f"[{status}] {file_path} | +{additions} -{deletions} | {size_kb}KB")

    return "\n".join(sorted(result))


def get_diff_between_commits(
    base_hash: str,
    head_hash: str = "HEAD",
    files_exclude_patterns: list[str] | None = None,
    files_include_patterns: list[str] | None = None,
    files_reinclude_patterns: list[str] | None = None,
    batch_size: int = 50,
    include_line_numbers: bool = False,
    repo_path: str = "/tmp/",
) -> str:
    """Get the diff between two commits, optionally filtering files by glob patterns.

    The filtering is done in a specific order to ensure correct pattern application:
    1. First, if include patterns are provided, only files matching those patterns are kept
    2. Then, exclude patterns are applied to filter out matching files
    3. Finally, reinclude patterns can override the exclude patterns to bring back specific files

    This order ensures that reinclude patterns only affect files that were actually excluded,
    preventing the reinclude of files that weren't matched by include patterns in the first place.

    Parameters
    ----------
    base_hash
        Base commit hash to compare from
    head_hash
        Head commit hash to compare to. If not provided, uses HEAD
    files_exclude_patterns
        List of glob patterns to exclude from the diff (relative to repo root).
        These patterns take precedence over include patterns.
    files_include_patterns
        List of glob patterns to include in the diff (relative to repo root).
        Note that exclude patterns will override these if there are conflicts.
    files_reinclude_patterns
        List of glob patterns to re-include files that were excluded by the exclude patterns.
        These patterns will only affect files that were previously excluded.
    repo_path
        Path to the git repository
    batch_size
        Number of files to process in each batch.
    include_line_numbers
        Whether to include line numbers in diff output (default: False)
    Returns
    -------
    :
        Diff as a string

    Raises
    ------
    DiffNotFoundError
        If there is an unexpected git error
    """
    try:
        repo = Repo(path=repo_path)
        changed_files = ""
        with LocalCommitsAvailability(repo_path, [base_hash, head_hash]):
            changed_files = repo.git.diff(base_hash, head_hash, "--name-only")

        if files_include_patterns and files_exclude_patterns:
            include_patterns = set(files_include_patterns)
            exclude_patterns = set(files_exclude_patterns)
            overlap = include_patterns & exclude_patterns
            if overlap:
                logger.warning(
                    f"Overlapping patterns found in include and exclude patterns: {overlap}. "
                    "Exclude patterns will take precedence as per git pathspec documentation."
                )

        filtered_files = []
        for f in changed_files.splitlines():
            if files_include_patterns and not any(fnmatch(f, pat) for pat in files_include_patterns):
                continue
            if files_exclude_patterns and any(fnmatch(f, pat) for pat in files_exclude_patterns):
                if not (files_reinclude_patterns and any(fnmatch(f, pat) for pat in files_reinclude_patterns)):
                    continue
            filtered_files.append(f)

        diffs = []
        for batch in batched(filtered_files, batch_size):
            diff = repo.git.diff(base_hash, head_hash, "--", *batch)
            if include_line_numbers and diff:
                # Git diff already includes line numbers in the @@ -X,Y +A,B @@ format
                # and shows line numbers in the context, so we don't need to modify it
                pass
            diffs.append(diff)
        return "\n".join(diffs)
    except GitCommandError as e:
        logger.exception(f"Unexpected error getting diff: {e}")
        raise DiffNotFoundError(f"Diff not found for commits {base_hash} and {head_hash}") from e


def get_diff_for_files(
    base_reference: str,
    file_paths: list[str] | None = None,
    head_reference: str = "HEAD",
    repo_path: str = "/tmp/",
    batch_size: int = 50,
) -> str:
    """Get the diff between two commits, optionally for specific files.

    Parameters
    ----------
    base_reference
        Base commit reference (e.g., "main", commit hash)
    file_paths
        List of file paths to get diff for
    head_reference
        Head commit reference (e.g., "feature", commit hash). Defaults to "HEAD"
    repo_path
        Path to git repository, by default "/tmp/"
    batch_size
        Number of files to process in each batch.

    Returns
    -------
    str
        Formatted string containing diffs for specified files or all changed files
    """
    repo = Repo(path=repo_path)
    with LocalCommitsAvailability(repo_path, [base_reference, head_reference]):
        if file_paths:
            # Get diff for specific files
            diffs = []
            for batch_file_paths in batched(iterable=file_paths, n=batch_size):
                try:
                    diff = repo.git.diff(base_reference, head_reference, "--", *batch_file_paths)
                    if diff:
                        diffs.append(diff)
                except GitCommandError:
                    # Skip files that don't exist or can't be diffed
                    logger.debug(f"Files {batch_file_paths} not found or can't be diffed in get_diff_for_files")
                    continue
            return "\n".join(diffs)
        else:
            # Get diff for all changed files
            return repo.git.diff(base_reference, head_reference)
