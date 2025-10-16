# lampe-describe

## Purpose

The `lampe-describe` package provides a collection of LLM-powered workflows for handling all sort of structured descriptions of entities. It includes:

- **PR Description:** Generate a description of a PR.
- **PR size (future):** Generate a size estimation of a PR.
- **PR Mermaid (future):** Generate a Mermaid diagram of a PR.

This package integrates with `lampe.core` and uses LlamaIndex for efficient management of conversational workflows and knowledge integration.

## How to Use

### PR description

The PR Description generation workflow generates clear and concise descriptions for pull requests by analyzing the diff changes. It produces two key sections:

- **What change is being made:** A single sentence summary of the major changes, written as an action statement
- **Why are these changes being made:** A brief 1-2 sentence explanation providing context and rationale for the changes

Example output:

```
## Description by LampeSDK
#### What change is being made?
...


#### Why are these changes being made?
...
```

To use the PR description workflow:

```python
data = {...}
input = PRDescriptionInput.model_validate(data)

result = asyncio.run(
    generate_pr_description(
        repository=input.repository,
        pull_request=input.pull_request,
    )
)

print(result.description)
```

### Running workflows

If your workspace is set up, you can run the classify workflow from the workspace root:

```sh
uv run generate_pr_description
```

These scripts are defined in the root `pyproject.toml` file under the `[project.scripts]` section.

## Adding Dependencies

To add a new dependency to the package, use the following command from the workspace root:

```sh
uv add --package lampe-describe <package-name>
```

This will add the package to the dependencies, update the lockfile, and install it automatically.

## Structure

See [packages/lampe-template/README.md](/packages/lampe-template/README.md) for details about the structure.
