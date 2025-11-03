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

To use the PR review workflow:

```python
data = {...}
input = PRReviewInput.model_validate(data)

result = asyncio.run(
    generate_pr_review(
        repository=input.repository,
        pull_request=input.pull_request,
        review_depth="standard",
        custom_guidelines=["Focus on security vulnerabilities", "Check for performance issues"]
    )
)

for review in result.reviews:
    print(f"File: {review.file_path}")
    print(f"Summary: {review.summary}")
    for line, comment in review.line_comments.items():
        print(f"Line {line}: {comment}")
```

### Running workflows

If your workspace is set up, you can run the review workflow from the workspace root:

```sh
uv run generate_pr_review
```

These scripts are defined in the root `pyproject.toml` file under the `[project.scripts]` section.

## Adding Dependencies

To add a new dependency to the package, use the following command from the workspace root:

```sh
uv add --package lampe-review <package-name>
```

This will add the package to the dependencies, update the lockfile, and install it automatically.

## Structure

See [packages/lampe-template/README.md](/packages/lampe-template/README.md) for details about the structure.


