LIST_CHANGED_FILES_DESCRIPTION = """
Lists all files that have changed between the current branch (or commit) and a specified base reference in a git repository.

Provides detailed statistics for each modified file.
- File path relative to repository root
- Number of lines added and removed
- File size after changes
- Change type (M=Modified, A=Added, D=Deleted)

Parameters:
- base_reference (string): The base branch or commit to compare against (e.g., a commit SHA provided by the user).

Returns:
- A newline-separated list of relative file paths with their statistics, that have changed between the current state and the base reference:
  [M/A/D] path/to/file.ext | +{additions} -{deletions} | {size}KB

Behavioral guidance:
- Always call this tool before requesting diffs or file contents, to minimize unnecessary data access.
- Use the output to drive further, more targeted tool calls.
"""  # noqa: E501


GIT_DIFF_DESCRIPTION = """
Returns the unified diff (line-by-line code changes) between the current branch (or commit) and a specified base reference. Can return either a full diff or diffs for specific files.

Parameters:
- base_reference (string): The base branch or commit to compare against (e.g., a commit SHA provided by the user).
- file_paths (list[string], optional): List of specific file paths to get diffs for. If not provided, returns diff for all changed files.


Returns:
- A single string containing the unified diff for the specified files or all changed files.

Behavioral guidance:
- For large PRs, use file_paths parameter to get diffs for specific files to avoid context window limitations.
- If the diff is too large or unclear, consider requesting file contents or smaller diffs for specific files.
"""  # noqa: E501


SHOW_COMMIT_DESCRIPTION = """
Shows detailed information and code changes for a specific commit in a git repository.

Use this tool to inspect the content, metadata, and diff introduced by a single commit. Helpful for understanding the context and impact of individual commits.

Parameters:
- commit_reference (string): The commit SHA or reference to show (e.g., a commit SHA provided by the user).

Returns:
- Commit metadata (SHA, author, date, message, stats) and the full diff for that commit.

Behavioral guidance:
- Use this tool when you need to analyze a specific commit in detail, such as for reviewing incremental
  changes or understanding commit history.
"""  # noqa: E501


GET_FILE_CONTENT_AT_COMMIT_DESCRIPTION = """
Retrieves the content of a specific file from a given commit reference in a git repository.

Use this tool to access the raw content of a file as it existed at a specific point in the repository's history. Useful for comparing file states across different commits or examining historical versions.

Parameters:
- commit_reference (string): The commit reference (e.g., a commit SHA provided by the user).
- file_path (string): Path to the file within the repository (relative to repository root).

Returns:
- The complete file content as a string. Returns empty string if the file doesn't exist at the specified commit.

Behavioral guidance:
- Use this tool when you need to examine the exact content of a file at a specific commit.
"""  # noqa: E501


SEARCH_IN_FILES_DESCRIPTION = """
Searches for a pattern in files within a specified directory at a specific commit in a git repository.

Use this tool to find occurrences of text patterns across files in a repository at a particular commit reference. Helpful for locating specific code elements or patterns within the codebase.

Parameters:
- pattern (string): The pattern to search for in files.
- relative_dir_path (string): Directory path to search within (relative to repository root).
- commit (string): The commit reference to search at (e.g., a commit SHA provided by the user).
- include_line_numbers (bool, optional): Whether to include line numbers in search results. Defaults to False.

Returns:
- Search results as a formatted string showing matching lines with line numbers. Returns "No matches found" if no matches exist.

Behavioral guidance:
- Use this tool when you need to locate specific code patterns or text within files at a particular commit.
- The search is performed using git grep which supports regular expressions for more advanced pattern matching.
"""  # noqa: E501


LIST_DIRECTORY_AT_COMMIT_DESCRIPTION = """
Lists directory contents at a specific commit (like ls). Use to understand project structure.

Parameters:
- relative_dir_path (string): Directory path relative to repository root (e.g. "src/", "packages/", "." for root).
- commit_hash (string): Commit reference to list at (e.g., branch name, commit SHA).
- repo_path (string): Path to the git repository.

Returns:
- Formatted listing of entries with type (blob=file, tree=dir), name, and full path.

Behavioral guidance:
- Use to orient yourself in the codebase before fetching diffs or file contents.
- List root (".") or parent dirs of files you are reviewing.
"""  # noqa: E501

FIND_FILES_BY_PATTERN_DESCRIPTION = """
Searches for files in a git repository using pattern matching.

Use this tool to find files that match a specified pattern in the repository. Helpful for locating files with specific extensions or within particular directory structures.

Parameters:
- pattern (string): The pattern to match files against (e.g., '*.py', 'src/**/*.md').

Returns:
- Formatted string containing paths of matching files. Returns "No files found" if no matches exist.

Behavioral guidance:
- Use this tool when you need to locate files matching specific patterns or extensions.
- The pattern matching uses git's pathspec syntax for flexible file path matching.
"""  # noqa: E501


# Quick review: context-window-aware descriptions

QUICK_REVIEW_LIST_DIRECTORY_DESCRIPTION = """
Lists directory contents at a commit (like ls). Use to understand project structure before fetching diffs.

Parameters:
- relative_dir_path (string): Directory path relative to repo root (e.g. "src/", "packages/", "." for root)
- commit_hash (string): Commit reference (head commit)
- repo_path (string): Repo path (pre-filled)

Behavioral guidance:
- Use to orient yourself in the codebase: list root or parent dirs of changed files.
- Entries show type (blob=file, tree=dir), name, and full path.
"""  # noqa: E501

QUICK_REVIEW_GET_DIFF_DESCRIPTION = """
Gets the diff for SPECIFIC files only. CRITICAL: Always pass file_paths with ONE file (or at most 2). Never omit file_paths — that returns the whole PR diff and blows the context window.

Parameters:
- base_reference (string): Base commit (pre-filled)
- head_reference (string): Head commit (pre-filled)
- file_paths (list[string]): REQUIRED. List of exactly 1 file path. E.g. ["src/foo.py"]. Never pass empty or omit — picking one file at a time is essential.
- repo_path (string): Repo path (pre-filled)

Behavioral guidance:
- Use this to understand the NATURE of changes in a file. Essential for knowing what the change intends.
- ONE file per call. Pick the most important file first (e.g. core logic, security-sensitive, config).
- After reading a diff, use search_in_files or get_file_content_at_commit to investigate specific concerns.
- Do NOT fetch diffs for all files. Be strategic: get enough to understand the PR purpose, then investigate.
"""  # noqa: E501

QUICK_REVIEW_SEARCH_IN_FILES_DESCRIPTION = """
Searches for a pattern in files using git grep at a specific commit. Primary tool for quick review.

Parameters:
- pattern (string): Pattern to search (supports regex)
- relative_dir_path (string): Directory to search (e.g. "src/", "." for repo root)
- commit_reference (string): Commit to search at (head commit)
- include_line_numbers (bool): True — use for quick review to get line numbers for targeted reads
- repo_path (string): Repo path (pre-filled)

Behavioral guidance:
- Use this FIRST to find relevant code before reading. Grep is lightweight.
- Search in directories of changed files only.
- Use line numbers from results to call get_file_content_at_commit with line_start/line_end.
"""  # noqa: E501

QUICK_REVIEW_GET_FILE_CONTENT_DESCRIPTION = """
Gets file content at a commit. CRITICAL: For files >300KB you MUST pass line_start and line_end. For quick review, ALWAYS use line ranges (max ~40 lines per read).

Parameters:
- commit_hash (string): Commit reference (head commit)
- file_path (string): File path within repo
- line_start (int, optional): 0-based start line — use for targeted reads
- line_end (int, optional): 0-based end line — keep range small (~20-40 lines)
- include_line_numbers (bool): True for readability
- repo_path (string): Repo path (pre-filled)

Behavioral guidance:
- ALWAYS use line_start and line_end. Never read full files.
- Get line numbers from search_in_files first, then read a small window.
- Large files without line range will return an error.
"""  # noqa: E501
