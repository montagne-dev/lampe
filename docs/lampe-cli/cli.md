# CLI Reference

Complete reference for the `lampe` command-line interface.

## Global Options

All commands support these global options:

- `--verbose/--no-verbose`: Enable verbose workflow logs (default: `--no-verbose`)

## Commands

### `lampe describe`

Generate a PR description from git diffs.

#### Usage

```sh
lampe describe [OPTIONS]
```

#### Required Options

- `--repo PATH`: Local path to the git repository
- `--base SHA`: Base commit SHA for the diff
- `--head SHA`: Head commit SHA for the diff

#### Optional Options

- `--title TEXT`: Title to provide context to the model (default: "Pull Request")
- `--variant [default|agentic]`: Choose the workflow variant (default: `default`)
- `--output [auto|console|github|gitlab|bitbucket]`: Output provider (default: `auto`)
- `--exclude PATTERN`: Glob patterns to exclude from the diff (repeatable)
- `--reinclude PATTERN`: Glob patterns to re-include after exclusion (repeatable)
- `--max-tokens INT`: Truncation budget for the diff content
- `--timeout-seconds INT`: Workflow timeout

#### Examples

**Default usage (diff: last commit → HEAD):**

```sh
lampe describe \
  --repo . \
  --title "$(git log -1 --pretty=%s)" \
  --base "$(git rev-parse HEAD~1)" \
  --head "$(git rev-parse HEAD)"
```

**Against main branch (diff: merge-base with origin/main → HEAD):**

```sh
lampe describe \
  --repo . \
  --title "$(git rev-parse --abbrev-ref HEAD)" \
  --base "$(git merge-base origin/main HEAD)" \
  --head "$(git rev-parse HEAD)"
```

**Agentic variant with JSON output:**

```sh
lampe describe \
  --repo . \
  --title "$(git rev-parse --abbrev-ref HEAD)" \
  --base "$(git merge-base origin/main HEAD)" \
  --head "$(git rev-parse HEAD)" \
  --variant agentic
```

**With exclusion patterns:**

```sh
lampe describe \
  --repo . \
  --title "Feature: Add new API endpoint" \
  --base "$(git merge-base origin/main HEAD)" \
  --head "$(git rev-parse HEAD)" \
  --exclude "*.lock" \
  --exclude "dist/**" \
  --exclude "node_modules/**"
```

**GitHub output (for CI):**

```sh
lampe describe \
  --repo . \
  --title "${{ github.event.pull_request.title }}" \
  --base "${{ github.event.pull_request.base.sha }}" \
  --head "${{ github.event.pull_request.head.sha }}" \
  --output github
```

#### Variants

##### Default Variant

The default variant uses a single LLM call with a well-structured prompt to generate the PR description. It's fast and cost-effective for most use cases.

##### Agentic Variant

The agentic variant uses a multi-step process with function calling to analyze the codebase more thoroughly. It can:

- Search the repository for context
- Analyze multiple files
- Make more informed decisions about what to include in the description

Use this variant for complex PRs or when you need more detailed analysis.

#### Output Providers

- **`auto`** (default): Automatically detect the environment (CI or local)
- **`console`**: Print to console (for local development)
- **`github`**: Post as a comment on GitHub PRs
- **`gitlab`**: Post as a comment on GitLab MRs
- **`bitbucket`**: Post as a comment on Bitbucket PRs

### `lampe review`

Generate a comprehensive code review for a pull request.

#### Usage

```sh
lampe review [OPTIONS]
```

#### Required Options

- `--repo PATH`: Local path to the git repository
- `--base SHA`: Base commit SHA for the diff
- `--head SHA`: Head commit SHA for the diff

#### Optional Options

- `--title TEXT`: Title to provide context to the model (default: "Pull Request")
- `--variant [multi-agent|diff-by-diff]`: Choose the review variant (default: `multi-agent`)
- `--output [auto|console|github|gitlab|bitbucket]`: Output provider (default: `auto`)
- `--review-depth [basic|standard|comprehensive]`: Review depth level (default: `standard`)
  - **`basic`**: Uses `gpt-5-nano` for faster, lighter reviews
  - **`standard`**: Uses `gpt-5` for balanced reviews (default)
  - **`comprehensive`**: Uses `gpt-5.1` for thorough, detailed reviews
- `--exclude PATTERN`: Glob patterns to exclude from the diff (repeatable)
- `--timeout-seconds INT`: Workflow timeout
- `--guideline TEXT`: Custom review guidelines to focus on (repeatable)

#### Model Selection

The model is automatically selected based on `--review-depth`:

| Review Depth    | Model Used   | Use Case                                            |
| --------------- | ------------ | --------------------------------------------------- |
| `basic`         | `gpt-5-nano` | Quick reviews, small changes, cost-effective        |
| `standard`      | `gpt-5`      | Balanced reviews, most common use case              |
| `comprehensive` | `gpt-5.1`    | Thorough reviews, critical changes, maximum quality |

#### Examples

**Standard review (default):**

```sh
lampe review \
  --repo . \
  --base "$(git merge-base origin/main HEAD)" \
  --head "$(git rev-parse HEAD)"
```

**Comprehensive review with GitHub output:**

```sh
lampe review \
  --repo . \
  --base "${{ github.event.pull_request.base.sha }}" \
  --head "${{ github.event.pull_request.head.sha }}" \
  --review-depth comprehensive \
  --output github
```

**Basic review for quick feedback:**

```sh
lampe review \
  --repo . \
  --base "$(git merge-base origin/main HEAD)" \
  --head "$(git rev-parse HEAD)" \
  --review-depth basic \
  --output console
```

**Diff-by-diff variant (parallel file reviews):**

```sh
lampe review \
  --repo . \
  --base "$(git merge-base origin/main HEAD)" \
  --head "$(git rev-parse HEAD)" \
  --variant diff-by-diff \
  --review-depth standard
```

**With custom guidelines:**

```sh
lampe review \
  --repo . \
  --base "$(git merge-base origin/main HEAD)" \
  --head "$(git rev-parse HEAD)" \
  --guideline "Focus on security vulnerabilities" \
  --guideline "Check for performance bottlenecks"
```

#### Variants

##### Multi-Agent Variant (default)

The multi-agent variant uses specialized agents that focus on different aspects of code quality:

- Design patterns
- Security
- Performance
- Code quality
- Testing

Each agent provides focused feedback in their domain.

##### Diff-by-Diff Variant

The diff-by-diff variant reviews each file change in parallel, providing focused analysis on individual file changes. This is particularly useful for:

- Large PRs with many files
- Parallel processing for faster reviews
- File-specific bug detection

### `lampe healthcheck`

Verify that the CLI is correctly installed and configured.

#### Usage

```sh
lampe healthcheck
```

This command checks:

- CLI installation
- Python environment
- Required dependencies
- Environment variables (API keys)

#### Example Output

```
✓ CLI installed correctly
✓ Python 3.11.5
✓ Dependencies installed
✓ OPENAI_API_KEY configured
✗ ANTHROPIC_API_KEY not configured (optional for default variant)
```

## Environment Variables

### Required

- `OPENAI_API_KEY`: Your OpenAI API key
- `ANTHROPIC_API_KEY`: Your Anthropic API key (required for agentic variant)

### Optional (for GitHub integration)

- `LAMPE_GITHUB_APP_ID`: GitHub App ID
- `LAMPE_GITHUB_APP_PRIVATE_KEY`: GitHub App private key

### Optional (for configuration)

Set these to override defaults:

- `LAMPE_LOG_LEVEL`: Log level (default: `INFO`)
- `LAMPE_TIMEOUT`: Default timeout in seconds
- `LAMPE_MAX_TOKENS`: Default token budget

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Configuration error (missing API keys, invalid options)
- `3`: Workflow error (LLM call failed, timeout)

## Troubleshooting

### "Missing API key" error

Make sure you've set the required environment variables:

```sh
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-..."
```

Or add them to your `.env` file.

### "Repository not found" error

Ensure the `--repo` path points to a valid git repository and that you have the necessary commits checked out.

### Timeout errors

Increase the timeout with `--timeout-seconds`:

```sh
lampe describe --timeout-seconds 300 ...
```

### Token budget exceeded

If your diff is too large, increase the token budget:

```sh
lampe describe --max-tokens 100000 ...
```

Or use exclusion patterns to reduce the diff size:

```sh
lampe describe --exclude "*.lock" --exclude "dist/**" ...
```

## Development

### Adding Dependencies

To add dependencies to the CLI package:

```sh
uv add --package lampe-cli <package-name>
```

This will update the lockfile and install the dependency for the workspace.

## Roadmap

- [x] Providers for CI (e.g., GitHub) to post descriptions directly to PRs
- [ ] Additional workflows (PR review, PR size, diagrams, etc.)
- [ ] Add more providers
- [ ] Configuration file support
