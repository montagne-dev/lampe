"""CLI entry point for running the agentic PR review from JSON input."""

import asyncio
import json
import sys


def main() -> None:
    """Run agentic PR review from a JSON input file. Usage: generate_pr_review <input_json_file>."""
    from lampe.core import initialize
    from lampe.core.tools import clone_repo
    from lampe.review.workflows.agentic_review import generate_agentic_pr_review
    from lampe.review.workflows.pr_review.data_models import PRReviewInput

    initialize()

    if len(sys.argv) < 2:
        print("Usage: generate_pr_review <input_json_file>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    repo_data = data.get("repository", {})
    if repo_data.get("url"):
        repository_path = clone_repo(
            repo_data["url"],
            head_ref=data.get("pull_request", {}).get("head_commit_hash"),
            base_ref=data.get("pull_request", {}).get("base_commit_hash"),
        )
        data = dict(data)
        data["repository"] = {"local_path": repository_path, "full_name": repo_data.get("full_name")}

    input_model = PRReviewInput.model_validate(data)

    result = asyncio.run(
        generate_agentic_pr_review(
            repository=input_model.repository,
            pull_request=input_model.pull_request,
            review_depth=input_model.review_depth,
            custom_guidelines=input_model.custom_guidelines,
            files_exclude_patterns=input_model.files_exclude_patterns or [],
        )
    )

    for agent_output in result.output:
        print(f"# Agent: {agent_output.agent_name}")
        print(f'**Focus Areas:** {", ".join(agent_output.focus_areas)}')
        print(f"**Global Summary:** {agent_output.summary}")
        print()
        for file_review in agent_output.reviews:
            print(f"## {file_review.file_path}")
            print(file_review.summary)
            for line_num, comment in file_review.line_comments.items():
                print(f"- Line {line_num}: {comment}")
            for c in file_review.structured_comments:
                if not c.muted:
                    print(f"- L{c.line_number} [{c.severity}] {c.comment}")
            print()
