LIST_CHANGED_FILES_DESCRIPTION = """
Lists all files that have changed between the current branch (or commit) and a specified base reference in a git repository.

Provides detailed statistics for each modified file.
- File path relative to repository root
- Number of lines added and removed
- File size after changes
- Change type (M=Modified, A=Added, D=Deleted)

Parameters:
- base_reference (string): The base branch or commit to compare against (e.g., 'main', 'origin/main', or a commit SHA).

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
- base_reference (string): The base branch or commit to compare against.
- file_paths (list[string], optional): List of specific file paths to get diffs for. If not provided, returns diff for all changed files.

Returns:
- A single string containing the unified diff for the specified files or all changed files.

Behavioral guidance:
- For large PRs, use file_paths parameter to get diffs for specific files to avoid context window limitations.
- If the diff is too large or unclear, consider requesting file contents or smaller diffs for specific files.
"""  # noqa: E501


GIT_DIFF_DESCRIPTION = """
Returns the unified diff (line-by-line code changes) between the current branch (or commit) and a specified base reference. Can return either a full diff or diffs for specific files.

Parameters:
- base_reference (string): The base branch or commit to compare against.
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
- commit_reference (string): The commit SHA or reference to show.

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
- commit_reference (string): The commit reference (e.g., 'main', 'HEAD', commit SHA).
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
- commit (string): The commit reference to search at.

Returns:
- Search results as a formatted string showing matching lines with line numbers. Returns "No matches found" if no matches exist.

Behavioral guidance:
- Use this tool when you need to locate specific code patterns or text within files at a particular commit.
- The search is performed using git grep which supports regular expressions for more advanced pattern matching.
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
