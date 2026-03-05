from llama_index.core.tools import FunctionTool

from lampe.core.tools.llm_integration.descriptions.repository_openai import (
    FIND_FILES_BY_PATTERN_DESCRIPTION,
    GET_FILE_CONTENT_AT_COMMIT_DESCRIPTION,
    GIT_DIFF_DESCRIPTION,
    LIST_DIRECTORY_AT_COMMIT_DESCRIPTION,
    QUICK_REVIEW_GET_DIFF_DESCRIPTION,
    QUICK_REVIEW_GET_FILE_CONTENT_DESCRIPTION,
    QUICK_REVIEW_LIST_DIRECTORY_DESCRIPTION,
    QUICK_REVIEW_SEARCH_IN_FILES_DESCRIPTION,
    SEARCH_IN_FILES_DESCRIPTION,
)
from lampe.core.tools.repository import (
    find_files_by_pattern,
    get_diff_for_files,
    get_file_content_at_commit,
    list_directory_at_commit,
    search_in_files,
)

git_tools_gpt_5_nano_agent_prompt = [
    FunctionTool.from_defaults(
        fn=list_directory_at_commit,
        name="list_directory_at_commit",
        description=LIST_DIRECTORY_AT_COMMIT_DESCRIPTION,
    ),
    FunctionTool.from_defaults(
        fn=get_diff_for_files,
        name="get_diff_for_files",
        description=GIT_DIFF_DESCRIPTION,
    ),
    FunctionTool.from_defaults(
        fn=get_file_content_at_commit,
        name="get_file_content_at_commit",
        description=GET_FILE_CONTENT_AT_COMMIT_DESCRIPTION,
    ),
    FunctionTool.from_defaults(
        fn=find_files_by_pattern,
        name="find_files_by_pattern",
        description=FIND_FILES_BY_PATTERN_DESCRIPTION,
    ),
    FunctionTool.from_defaults(
        fn=search_in_files,
        name="search_in_files",
        description=SEARCH_IN_FILES_DESCRIPTION,
    ),
]

# Quick review tools: ls + single-file diff + grep + targeted reads
quick_review_tools = [
    FunctionTool.from_defaults(
        fn=list_directory_at_commit,
        name="list_directory_at_commit",
        description=QUICK_REVIEW_LIST_DIRECTORY_DESCRIPTION,
    ),
    FunctionTool.from_defaults(
        fn=get_diff_for_files,
        name="get_diff_for_files",
        description=QUICK_REVIEW_GET_DIFF_DESCRIPTION,
    ),
    FunctionTool.from_defaults(
        fn=search_in_files,
        name="search_in_files",
        description=QUICK_REVIEW_SEARCH_IN_FILES_DESCRIPTION,
    ),
    FunctionTool.from_defaults(
        fn=get_file_content_at_commit,
        name="get_file_content_at_commit",
        description=QUICK_REVIEW_GET_FILE_CONTENT_DESCRIPTION,
    ),
]
