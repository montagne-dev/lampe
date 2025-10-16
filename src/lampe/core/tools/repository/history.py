import logging

from git import Repo

from lampe.core.loggingconfig import LAMPE_LOGGER_NAME

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)


def show_commit(commit_reference: str, repo_path: str = "/tmp/") -> str:
    """Show the contents of a commit.

    This function shows the contents of a commit, including the commit details and diffs.

    Parameters
    ----------
    commit_reference
        Commit reference (e.g., "main", commit hash)
    repo_path
        Path to git repository, by default "/tmp/"

    Returns
    -------
    str
        Formatted string containing commit details and diffs
    """
    repo = Repo(path=repo_path)
    commit = repo.commit(commit_reference)
    output = [
        f"Commit: {commit.hexsha}\n"
        f"Author: {commit.author}\n"
        f"Date: {commit.authored_datetime}\n"
        f"Message: {commit.message}\n"
        f"Files: {len(commit.stats.files)} files changed\n"
        f"Changes: +{commit.stats.total['insertions']} -{commit.stats.total['deletions']}\n"
        f"Modified files:\n" + "\n".join(f"  - {f}" for f in commit.stats.files)
    ]
    if commit.parents:
        parent = commit.parents[0]
        diff = parent.diff(commit, create_patch=True)
    else:
        diff = commit.diff(None, create_patch=True)
    for d in diff:
        output.append(f"\n--- {d.a_path}\n+++ {d.b_path}\n")
        if d.diff:
            output.append(str(d.diff))
    return "".join(output)


def get_commit_log(max_count: int, repo_path: str = "/tmp/") -> str:
    """Get the log of commits for a repository.

    This function gets the log of commits for a repository, including the commit details
    and the list of files path that were changed.

    Parameters
    ----------
    max_count
        Maximum number of commits to return
    repo_path
        Path to git repository, by default "/tmp/"

    Returns
    -------
    str
        Formatted string containing commit details and list of files that were changed
    """
    repo = Repo(path=repo_path)
    commits = list(repo.iter_commits(max_count=max_count))
    log = []
    for commit in commits:
        log.append(
            f"Commit: {commit.hexsha}\n"
            f"Author: {commit.author}\n"
            f"Date: {commit.authored_datetime}\n"
            f"Message: {commit.message}\n"
            f"Files: {len(commit.stats.files)} files changed\n"
            f"Changes: +{commit.stats.total['insertions']} -{commit.stats.total['deletions']}\n"
            f"Modified files:\n" + "\n".join(f"  - {f}" for f in commit.stats.files)
        )
    return "\n".join(log)
