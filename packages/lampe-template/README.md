# lampe-template

This package serves as a template and example for creating new packages within the `lampe-sdk` [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/#workspace-layouts).

## Purpose

- **Demonstrate Integration:** Shows how to build a package that depends on and imports from `lampe.core`, the main logic library of the SDK.
- **Scaffold for New Packages:** Provides a minimal, ready-to-copy structure for new workspace members.
- **Consistent Development:** Ensures all packages in the workspace share dependencies and Python version, simplifying development and maintenance.

## Structure

### Why this structure?

> The `src/lampe/template` folder ensures that, when installed as an SDK, you can always import using the pattern `from lampe.xxx import yyy`. Where xxx is a package name (i.e. `template`). If the folder was instead `src/lampe_template/`, you would have to import as `from lampe_template import yyy` or `from lampe_other import yyy`, breaking consistency across packages. This is also why the `pyproject.toml` includes a note and a section [`[tool.hatch.build.targets.wheel]`](packages/lampe-template/pyproject.toml) to specify the source folder.

```
├── pyproject.toml
├── README.md
├── src
│   └── lampe
│       └── template
│           ├── __init__.py
│           └── template_workflow.py
└── tests
    └── unit
        └── test_template_workflow.py
```

## Example Usage

The main class in this template is `TemplateWorkflow`, which imports and uses a constant from `lampe.core`.

```py
from lampe.template import TemplateWorkflow
async def main():
    w = TemplateWorkflow(timeout=10, verbose=False)
    result = await w.run()
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

### Visualizing Workflows

You can visualize all possible flows of a workflow using:

```py
from llama_index.utils.workflow import draw_all_possible_flows

draw_all_possible_flows(TemplateWorkflow, filename="template_workflow.html")
```

## How to Use

- Use this package as a starting point for new workspace members.
- Update the code and metadata to fit your new package's purpose.
- Import from `lampe.core` or other workspace packages as needed.

## Running the Example

If your workspace is set up, you can run the template workflow from the workspace root:

```sh
uv run template
```

## Adding and Running Scripts

You can easily add a script entry point to your package and run workflows using `uv run <script_name>`. This is useful for exposing workflows or utilities as command-line scripts.

### 1. Define a Script in `pyproject.toml`

In your package's `pyproject.toml`, add an entry under `[project.scripts]` (in the root `pyproject.toml` if you want workspace-wide access, or in your package's own `pyproject.toml` for local scripts):

```toml
[project.scripts]
template = "lampe.template:main"
```

This example exposes the `main` function from `lampe.template` as the `template` script.

### 2. Implement the Entry Point

Make sure your package exposes the function you reference. For example, in `src/lampe/template/template_workflow.py`:

```python
def main():
    asyncio.run(run_workflow())
```

And in `src/lampe/template/__init__.py`:

```python
from lampe.template.template_workflow import main
```

### 3. Run the Script

From the workspace root, you can now run your script with:

```sh
uv run template
```

This will execute the `main` function you defined.

You can add more scripts by following the same pattern: define a function, expose it in your package, and add it to `[project.scripts]`.
