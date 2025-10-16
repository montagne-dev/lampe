# Lampe SDK

## Project Structure & Purpose

This repository is organized as a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/#workspace-layouts), allowing you to manage multiple related Python packages in a single repository with a shared lockfile and consistent dependencies.

### Workspace Layout

- **Root Project (`lampe-sdk`)**: The main entry point and workspace root.
- **`packages/lampe-template`**: A template package designed to demonstrate or scaffold new packages that integrate with the core logic.
- **`src/lampe/core`**: The core library, providing foundational logic and constants for the SDK.

### Why a Template?

The `lampe-template` package exists to provide a starting point for new packages that need to integrate with `lampe.core`. It demonstrates:

- How to depend on and import from `lampe.core` using the workspace setup.
- How to structure a minimal package with its own `pyproject.toml`, source directory, and public API.
- How to expose scripts/entry points via the workspace's configuration.

### TODO: Add an explanation on how to create a new template and how to install it in the root

1. we want to add it as a workspace and add it in the pyroject.toml dependencies.
   is there a command to do so ?

### How Integration Works

- The root `pyproject.toml` declares `lampe-template` as workspace members.
- `lampe-template` imports from `lampe.core` (see `workflow.py`), showing how to build on the core logic.
- The workspace ensures that all packages use the same Python version and dependency set, avoiding conflicts.

This function demonstrates how a template package can use core constants and logic.

### Entrypoints

The root `pyproject.toml` defines scripts:

- `core` runs `lampe.core:main`
- `template` runs `lampe.template:workflow`

You can invoke these via `uv run core` or `uv run template` from the workspace root to run a function.

### Future Proofing

This workspace structure is designed to scale with your project's growth. As documented in uv's workspace section:

- As complexity increases, packages can be split into smaller, composable units
- Each package maintains its own dependencies and version constraints
- Packages can be tested and developed independently
- When needed, packages can be extracted into standalone modules

This approach provides flexibility: packages can start in the workspace for rapid development, then graduate to independent repositories as they mature, without requiring major architectural changes.

## Getting Started

1. Install dependencies:
   ```sh
   uv sync
   uv run pre-commit install
   ```
2. Run the core script:
   ```sh
   uv run core
   ```
3. Run the template workflow:
   ```sh
   uv run template
   ```
4. Run the unit tests:
   ```sh
   uv run pytest # Using pyproject.toml pytest config
   ```

### System Requirements: Git Version Requirements

The `lampe-sdk` requires **Git version 2.49.0 or higher** for proper functionality. The SDK requires the `--revision` flag introduced in Git 2.49.0 for efficient repository cloning and branch operations.

#### Checking Your Git Version

```sh
git --version
```

> git version 2.49.0

#### Installing/Upgrading Git

See documentation from [Git website](https://git-scm.com/download).

**Requirement:** The SDK will log critical warnings at startup if your Git version is insufficient (2.49.0 or higher required). Attempting to use `clone_repo` with an older Git version will raise a RuntimeError.

### Pre-commit Configuration

The project uses pre-commit hooks to ensure code quality and consistency. The hooks are configured in `.pre-commit-config.yaml` and run at different stages:

On commit:

- Ruff for Python code linting and formatting (line length, style, imports)
- Code cleanliness checks:
  - Remove trailing whitespace
  - Fix end of file newlines
  - Validate YAML files
  - Prevent large file commits
  - Remove debug statements
  - Detect merge conflicts
- Prettier for consistent formatting of non-Python files (JSON, Markdown, etc)

On push:

- Currently, pyright type checking and pytest are run via GitHub Actions instead of pre-commit hooks due to limitations with running `uv` commands in the pre-commit GitHub action environment. In the future, these checks will be migrated to pre-commit hooks for local push validation, while keeping the GitHub Actions workflows separate to avoid duplicate CI runs. Note that the GitHub Actions pre-commit workflow is configured to skip pyright and pytest checks to avoid duplicate runs.

## Dependency Management

The workspace uses a centralized dependency management system with `uv`. Here's how to effectively manage dependencies across packages:

### Adding Package-Specific Dependencies

To add a dependency that's only required for a specific package:

```sh
uv add --package lampe-template httpx
```

This command will:

1. Add the dependency to the package's `pyproject.toml`
2. Update the workspace's `uv.lock` file
3. Make the dependency available to all packages in the workspace

#### Important Notes

1. **Workspace-wide Availability:**

   - Dependencies added to any package's `pyproject.toml` are available workspace-wide through the single `uv.lock` file
   - This means you can use a dependency in any package once it's added to any package's `pyproject.toml`

2. **Package Independence:**

   - Always declare a dependency in every package that requires it, even if it's already available through the workspace
   - This ensures that if a package is extracted into a standalone module in the future, its `pyproject.toml` accurately lists all its true dependencies
   - It also makes the package's requirements explicit and self-documenting

3. **Best Practices:**
   - Keep package-specific dependencies minimal and well-documented
   - Document why a dependency is package-specific in the package's README
   - Regularly review dependencies to identify candidates for global promotion
   - When a dependency is used by multiple packages, consider moving it to the root `pyproject.toml`

#### Example Workflow

1. Adding a new package-specific dependency:

   ```sh
   uv add --package lampe-template httpx
   ```

2. Moving a dependency to global scope:

   ```sh
   # Add to root pyproject.toml
   uv add httpx

   # Remove from package pyproject.toml
   uv remove --package lampe-template httpx
   ```

TLDR: Always declare package-specific dependencies in the respective package's `pyproject.toml`, even if they're already available through the workspace. This ensures package independence and clear dependency tracking.
