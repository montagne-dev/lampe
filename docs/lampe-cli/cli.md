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
