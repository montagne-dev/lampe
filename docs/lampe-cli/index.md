# LampeCLI Overview

LampeCLI provides a unified command-line interface for running Lampe workflows locally or in CI/CD environments.

## What is LampeCLI?

`lampe-cli` provides a single binary `lampe` to run Lampe workflows from the command line in local or CI contexts. It integrates with `lampe.core` and workflow packages like `lampe-describe`, keeping providers (console, GitHub, etc.) abstracted behind a clean interface.

## Key Features

- **Local Development**: Run workflows directly from your terminal
- **CI/CD Integration**: Seamlessly integrate with GitHub Actions, GitLab CI, and Bitbucket Pipelines
- **Multiple Providers**: Output to console, GitHub, GitLab, or Bitbucket
- **Flexible Configuration**: Extensive options for customization
- **Multiple Variants**: Support for default and agentic generation modes

## Installation

### Workspace Installation

From the repository root, install the CLI in editable mode so the `lampe` command is available:

```sh
uv tool install --editable .
uv tool install git+https://github.com/montagne-dev/lampe.git
```

After this, you can run the CLI as:

```sh
lampe --help
```

### Using as a Dependency

You can also use `lampe-sdk` as a dependency in your own Python project:

```sh
# Using a branch name
uv add git+https://github.com/montagne-dev/lampe.git@branch-name --upgrade

# Using a tag/version
uv add git+https://github.com/montagne-dev/lampe.git@v0.1.0

# Not yet published
# Using PyPI
uv add lampe-sdk

# Using pip
pip install lampe-sdk
```

## Environment Configuration

You must set the following environment variables before running any CLI commands:

| Variable            | Default | Purpose                             |
| ------------------- | ------- | ----------------------------------- |
| `OPENAI_API_KEY`    | `unset` | API key for OpenAI LLM provider.    |
| `ANTHROPIC_API_KEY` | `unset` | API key for Anthropic LLM provider. |

Example `.env`:

```
OPENAI_API_KEY="sk-.."
ANTHROPIC_API_KEY="sk-.."
```

## Quick Start

Generate a PR description for your current branch:

```sh
lampe describe \
  --repo . \
  --title "$(git log -1 --pretty=%s)" \
  --base "$(git rev-parse HEAD~1)" \
  --head "$(git rev-parse HEAD)"
```

## Available Commands

- **`describe`**: Generate PR descriptions from git diffs
- **`review`**: Generate comprehensive code reviews for pull requests
- **`check-reviewed`**: Check if a PR has already been reviewed by the token user
- **`healthcheck`**: Verify CLI installation and configuration

For detailed usage instructions, see the [CLI Reference](cli.md).

## Next Steps

- [CLI Reference](cli.md) - Detailed command documentation
- [GitHub Actions Integration](../lampe-ci/github-actions.md) - Use LampeCLI in GitHub workflows
- [GitLab CI Integration](../lampe-ci/gitlab-ci.md) - Use LampeCLI in GitLab pipelines
- [Bitbucket Pipelines Integration](../lampe-ci/bitbucket-pipelines.md) - Use LampeCLI in Bitbucket pipelines
