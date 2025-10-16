# lampe-cli

## Purpose

`lampe-cli` provides a single binary `lampe` to run Lampe workflows from the command line in local or CI contexts. For now, it supports running the PR description workflow locally and printing the result to the console.

It integrates with `lampe.core` and the `lampe-describe` workflow package, keeping providers (console, GitHub, etc.) abstracted behind a clean interface.

## Install (workspace)

From the repository root, install the CLI in editable mode so the `lampe` command is available:

```sh
uv tool install --editable .
```

After this, you can run the CLI as:

```sh
lampe --help
```

## Usage

### Generate a PR description locally (console output)

You must provide a repository path and the diff range (base and head SHAs). The PR title is used for prompt context.

- Default (diff: last commit → HEAD):

```sh
lampe describe \
  --repo . \
  --title "$(git log -1 --pretty=%s)" \
  --base "$(git rev-parse HEAD~1)" \
  --head "$(git rev-parse HEAD)"
```

- Against main branch (diff: merge-base with origin/main → HEAD):

```sh
lampe describe \
  --repo . \
  --title "$(git rev-parse --abbrev-ref HEAD)" \
  --base "$(git merge-base origin/main HEAD)" \
  --head "$(git rev-parse HEAD)"
```

- Agentic variant, JSON output:

```sh
lampe describe \
  --repo . \
  --title "$(git rev-parse --abbrev-ref HEAD)" \
  --base "$(git merge-base origin/main HEAD)" \
  --head "$(git rev-parse HEAD)" \
  --variant agentic
```

### Options

- `--repo PATH` (required): Local path to the git repository.
- `--base SHA` (required): Base commit SHA for the diff.
- `--head SHA` (required): Head commit SHA for the diff.
- `--title TEXT` (default: "Pull Request"): Title to provide context to the model.
- `--variant [default|agentic]` (default: `default`): Choose the workflow variant.
- `--output [auto|console|github|gitlab|bitbucket]` (default: `auto`): Output provider.
- `--exclude PATTERN` (repeatable): Glob patterns to exclude from the diff.
- `--reinclude PATTERN` (repeatable): Glob patterns to re-include after exclusion.
- `--max-tokens INT`: Truncation budget for the diff content.
- `--timeout-seconds INT`: Workflow timeout.
- `--verbose/--no-verbose`: Verbose workflow logs.

## Roadmap

- [x] Providers for CI (e.g., GitHub) to post descriptions directly to PRs.
- [ ] Additional workflows (PR size, diagrams, etc.).

## Development

- To add dependencies to this package:

```sh
uv add --package lampe-cli <package-name>
```

This will update the lockfile and install the dependency for the workspace.
