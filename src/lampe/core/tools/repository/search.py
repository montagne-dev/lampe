import logging

from git import GitCommandError, Repo

from lampe.core.loggingconfig import LAMPE_LOGGER_NAME

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)


def search_in_files(
    pattern: str,
    relative_dir_path: str,
    commit_reference: str,
    include_line_numbers: bool = False,
    repo_path: str = "/tmp/",
) -> str:
    """Search for a pattern in files within a directory at a specific commit.

    Parameters
    ----------
    pattern
        Pattern to search for
    relative_dir_path
        Directory path to search in
    commit_reference
        Commit reference to search at
    include_line_numbers
        Whether to include line numbers in search results (default: False)
    repo_path
        Path to the git repository, by default "/tmp/"

    Returns
    -------
    str
        Search results as a string
    """
    try:
        repo = Repo(path=repo_path)
        if include_line_numbers:
            grep_output = repo.git.grep("-n", pattern, f"{commit_reference}:{relative_dir_path}")
        else:
            grep_output = repo.git.grep(pattern, f"{commit_reference}:{relative_dir_path}")
        if grep_output:
            return f"```grep\n{grep_output}\n```"
        return "No matches found"
    except GitCommandError as e:
        if e.status == 128:
            return "No matches found"
        return f"Error executing git grep: {str(e)}"


def find_files_by_pattern(pattern: str, repo_path: str = "/tmp/") -> str:
    """Search for files using git ls-files and pattern matching.

    Parameters
    ----------
    pattern
        Pattern to search for (e.g. "*.py", "src/**/*.md")
    repo_path
        Path to git repository

    Returns
    -------
    str
        Formatted string containing matching file paths
    """
    repo = Repo(path=repo_path)
    try:
        # Filter files matching pattern using git's pathspec matching
        matching = repo.git.ls_files("--", pattern).splitlines()

        if not matching:
            return "No files found"

        return f"```shell\n{'\n'.join(matching)}\n```"

    except GitCommandError as e:
        logger.exception(f"Error finding files: {e}")
        return f"Error: {str(e)}"
