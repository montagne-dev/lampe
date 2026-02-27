# lampe-review

## Purpose

The `lampe-review` package provides LLM-powered workflows for performing detailed code reviews of pull requests. It includes:

- **PR Review:** Generate detailed code reviews with inline comments for specific files/lines.
- **Configurable Review Depth:** Basic, standard, or comprehensive review levels.
- **Custom Guidelines:** Specify custom review criteria and focus areas.

This package integrates with `lampe.core` and uses LlamaIndex for efficient management of conversational workflows and knowledge integration.

## How to Use

### PR Review

The PR Review generation workflow analyzes code changes and provides detailed feedback with inline comments. It supports three review depth levels:

- **Basic:** Focus on critical issues, security vulnerabilities, and obvious bugs
- **Standard:** Add code quality, best practices, and potential edge cases
- **Comprehensive:** Deep analysis including performance, architecture, maintainability, and test coverage

Example output:

```
## Code Review by LampeSDK

### src/example.py
**Summary:** Overall good implementation, minor improvements suggested

**Line Comments:**
- Line 15: Consider adding null check here
- Line 42: This could cause performance issues with large datasets
```

To use the PR review workflow (agentic orchestrator with intent, skills, and validation agents):

```python
from lampe.review.workflows import generate_agentic_pr_review
from lampe.review.workflows.pr_review.data_models import PRReviewInput, ReviewDepth

# ... build repository and pull_request from your context ...

result = asyncio.run(
    generate_agentic_pr_review(
        repository=repository,
        pull_request=pull_request,
        review_depth=ReviewDepth.STANDARD,
        custom_guidelines=["Focus on security vulnerabilities", "Check for performance issues"],
    )
)

for agent_output in result.output:
    for file_review in agent_output.reviews:
        print(f"File: {file_review.file_path}")
        print(f"Summary: {file_review.summary}")
        for line, comment in file_review.line_comments.items():
            print(f"Line {line}: {comment}")
```

You can also run review via the CLI: `lampe review --repo . --base <base_sha> --head <head_sha>` (see `lampe-cli` package). From the workspace root, a script is available for JSON-file input: `uv run generate_pr_review <input_json_file>` (input must contain `repository` and `pull_request`; optional `repository.url` triggers a clone).

## Adding Dependencies

To add a new dependency to the package, use the following command from the workspace root:

```sh
uv add --package lampe-review <package-name>
```

This will add the package to the dependencies, update the lockfile, and install it automatically.

## Structure

See [packages/lampe-template/README.md](/packages/lampe-template/README.md) for details about the structure.
