# GitHub Actions Integration 🔦

The Lampe SDK includes a GitHub Action that makes it easy to integrate PR description generation and code review into your GitHub workflows. This action automatically fetches the necessary commit history and runs Lampe CLI commands in your GitHub workflows.

## Features

- **Automatic Git History Fetching**: Includes the `fetch-through-merge-base` functionality to ensure all PR commits are available
- **Multiple Commands**: Support for `describe`, `review`, and `healthcheck` commands
- **Flexible Configuration**: Extensive options for customization
- **Multiple Output Providers**: Support for console, GitHub, GitLab, and Bitbucket outputs
- **Two Generation Variants**: Default and agentic modes

## Quick Start

Add this to your `.github/workflows/pr-description.yml`:

```yaml
name: Generate PR Description
on:
  pull_request:

jobs:
  describe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}
      - uses: montagne-dev/lampe@main
        with:
          command: describe
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Usage Patterns

### Pull Request Open Event Only

To run the action only when a pull request is opened (not on every push), use the `opened` event trigger:

```yaml
name: Generate PR Description
on:
  pull_request:
    types: [opened]

jobs:
  describe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}
      - uses: montagne-dev/lampe@main
        with:
          command: describe
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Advanced Usage

```yaml
name: Generate PR Description
on:
  pull_request:

jobs:
  describe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}
      - uses: montagne-dev/lampe@main
        with:
          command: describe
          variant: agentic
          output: github
          files_exclude: "*.md,*.txt"
          files_reinclude: "docs/*.md"
          max_tokens: 12000
          timeout_seconds: 300
          verbose: true
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          LAMPE_GITHUB_APP_ID: ${{ secrets.LAMPE_GITHUB_APP_ID }}
          LAMPE_GITHUB_APP_PRIVATE_KEY: ${{ secrets.LAMPE_GITHUB_APP_PRIVATE_KEY }}
```

## Commands

### `describe`

Generates a comprehensive PR description based on the changes in the pull request.

**Features:**

- Analyzes file changes and commit history
- Generates structured descriptions
- Supports multiple output formats
- Configurable file inclusion/exclusion

### `review`

Performs code review analysis on the pull request.

**Features:**

- Identifies potential issues and improvements
- Provides actionable feedback
- Supports different review styles
- Integrates with GitHub's review system

### `healthcheck`

Verifies that the Lampe SDK is properly configured and can connect to required services.

**Features:**

- Validates API keys
- Tests LLM connectivity
- Checks configuration
- Reports system status

## Configuration Options

### Input Parameters

| Input             | Description                                                          | Required | Default                  |
| ----------------- | -------------------------------------------------------------------- | -------- | ------------------------ |
| `command`         | The Lampe CLI command to run (`describe`, `review`, `healthcheck`)   | Yes      | `describe`               |
| `repo`            | Repository path                                                      | No       | `.`                      |
| `title`           | PR title (for local runs)                                            | No       | `Pull Request`           |
| `base_ref`        | Base ref for comparison                                              | No       | `${{ github.base_ref }}` |
| `head_ref`        | Head ref for comparison                                              | No       | `${{ github.head_ref }}` |
| `output`          | Output provider (`auto`, `console`, `github`, `gitlab`, `bitbucket`) | No       | `auto`                   |
| `variant`         | Generation variant (`default`, `agentic`)                            | No       | `default`                |
| `files_exclude`   | Comma-separated list of file patterns to exclude                     | No       | -                        |
| `files_reinclude` | Comma-separated list of file patterns to reinclude                   | No       | -                        |
| `max_tokens`      | Maximum tokens for truncation                                        | No       | `8000`                   |
| `timeout_seconds` | Timeout in seconds                                                   | No       | -                        |
| `verbose`         | Enable verbose output                                                | No       | `false`                  |
| `deepen_length`   | Git fetch deepen length for merge-base                               | No       | `10`                     |

### Environment Variables

The following environment variables can be set as GitHub secrets:

| Variable                       | Description                          | Required               |
| ------------------------------ | ------------------------------------ | ---------------------- |
| `OPENAI_API_KEY`               | OpenAI API key for LLM calls         | Yes (for LLM features) |
| `ANTHROPIC_API_KEY`            | Anthropic API key for LLM calls      | Yes (for LLM features) |
| `LAMPE_GITHUB_APP_ID`          | GitHub App ID for GitHub integration | No                     |
| `LAMPE_GITHUB_APP_PRIVATE_KEY` | GitHub App private key               | No                     |

## Output Providers

- **`auto`**: Automatically detects the platform (GitHub, GitLab, Bitbucket)
- **`console`**: Outputs to the GitHub Actions log
- **`github`**: Integrates with GitHub's PR system
- **`gitlab`**: Integrates with GitLab's merge request system
- **`bitbucket`**: Integrates with Bitbucket's pull request system

## Generation Variants

### `default`

Standard generation using the default Lampe workflow.

### `agentic`

Advanced generation using agentic workflows with enhanced reasoning capabilities.

## File Filtering

Use `files_exclude` and `files_reinclude` to control which files are analyzed:

```yaml
files_exclude: "*.md,*.txt,*.json"
files_reinclude: "docs/*.md,README.md"
```

## Examples

### Complete Workflow with Multiple Commands

```yaml
name: Lampe Analysis
on:
  pull_request:

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}

      # Health check
      - name: Health Check
        uses: montagne-dev/lampe@main
        with:
          command: healthcheck
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      # Generate description
      - name: Generate Description
        uses: montagne-dev/lampe@main
        with:
          command: describe
          variant: agentic
          output: github
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      # Generate review
      - name: Generate Review
        uses: montagne-dev/lampe@main
        with:
          command: review
          variant: agentic
          output: github
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Custom Configuration

```yaml
name: Custom Lampe Configuration
on:
  pull_request:

jobs:
  custom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}
      - uses: montagne-dev/lampe@main
        with:
          command: describe
          variant: agentic
          output: console
          files_exclude: "*.md,*.txt,*.json,*.yml,*.yaml"
          files_reinclude: "docs/*.md,README.md"
          max_tokens: 15000
          timeout_seconds: 600
          verbose: true
          deepen_length: 20
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Review Command

```yaml
name: Review PR
on:
  pull_request:

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}
      - uses: montagne-dev/lampe@main
        with:
          command: review
          variant: agentic
          output: github
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Health Check

```yaml
name: Health Check
on:
  pull_request:

jobs:
  healthcheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}
      - uses: montagne-dev/lampe@main
        with:
          command: healthcheck
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Publishing the Action

To make this action available on GitHub Marketplace:

1. **Create a Release**: Tag a version (e.g., `v1.0.0`)
2. **Update References**: Change `@main` to `@v1.0.0` in usage examples
3. **Marketplace**: The action will automatically appear in the marketplace

## Local Testing

To test the action locally:

1. Use `./` instead of `montagne-dev/lampe@main` in workflows
2. Run the example workflows in `.github/workflows/`
3. Check logs for any issues

## Migration from Current Workflow

To migrate from the current `pr_description.yml`:

1. Replace the manual steps with the new action
2. Move environment variables to the `env` section
3. Use the `command: describe` input
4. Test with a small PR first

## Troubleshooting

### Common Issues

1. **API Key Issues**: Ensure your API keys are properly set in GitHub secrets
2. **Timeout Issues**: Increase `timeout_seconds` for large repositories
3. **Memory Issues**: Reduce `max_tokens` for very large changes
4. **Git History Issues**: Increase `deepen_length` for repositories with deep history

### Debug Mode

Enable verbose output to see detailed logs:

```yaml
- uses: montagne-dev/lampe@main
  with:
    command: describe
    verbose: true
```

### Health Check

Always run a health check first to verify your setup:

```yaml
- uses: montagne-dev/lampe@main
  with:
    command: healthcheck
```

## Security Considerations

- All API keys are passed as environment variables
- No sensitive data is logged
- Git operations are performed safely with proper ref handling

## Support

For issues and questions:

- GitHub Issues: [montagne-dev/lampe](https://github.com/montagne-dev/lampe/issues)
- Documentation: [Lampe SDK Docs](https://docs.montagne.dev/lampe-sdk)
