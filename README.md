# lampe-sdk 🔦

> Lampe is the SDK part of the montagne-dev (🏔️🏕️🔦) project.

## Using `lampe-sdk`

You can use `lampe-sdk` as a dependency in your own Python project. To do so:

1. **Install the SDK**:

   ```sh
   # Using a branch name
   uv add https://github.com/montagne-dev/lampe.git@branch-name --upgrade
   # Using a tag/version
   uv add https://github.com/montagne-dev/lampe.git@v0.1.0
   # Using pypi
   uv add lampe-sdk
   # Using pip
   pip install lampe-sdk
   ```

2. **Set Up Environment Variables**

You must set the following two environment variables before running any CLI commands:

| Variable            | Default | Purpose                             |
| ------------------- | ------- | ----------------------------------- |
| `OPENAI_API_KEY`    | `unset` | API key for OpenAI LLM provider.    |
| `ANTHROPIC_API_KEY` | `unset` | API key for Anthropic LLM provider. |

Example `.env`:

```
OPENAI_API_KEY="sk-.."
ANTHROPIC_API_KEY="sk-.."
```

3. **Import and Use the SDK**

   ```python
    # Initialize the SDK (required)
    from lampe.describe import PRDescriptionWorkflow, PRDescriptionStartEvent, generate_pr_description
    initialize()

    # Import and use SDK features
    from lampe.describe import PR
    workflow = PRDescriptionWorkflow(truncation_tokens=truncation_tokens, timeout=timeout, verbose=verbose)
    result = await workflow.run(
        start_event=PRDescriptionStartEvent(
            pr_title=pull_request.title,
            repository=repository,
            pull_request=pull_request,
            files_exclude_patterns=files_exclude_patterns,
        )
    )
    # Or using entrypoint
    data = {...} # Add required informations of PRDescriptionInput
    input = PRDescriptionInput.model_validate(data)

    result = asyncio.run(
        generate_pr_description(
            repository=input.repository,
            pull_request=input.pull_request,
            files_exclude_patterns=input.files_exclude_patterns,
            files_reinclude_patterns=input.files_reinclude_patterns,
        )
    )
    print(result.description)
   ```

The SDK must be initialized before use. The initialization will set up logging and telemetry (if configured).

### Documentation

```

uv run mkdocs serve
Serving on http://127.0.0.1:8000/
# build the documentation
uv run mkdocs build

```

Open a bowser to http://127.0.0.1:8000/ to view the docs

## LLM Configuration

Configure the LITELLM proxy environment variables in your `.env` file to enable LLM calls. Multiple models are in used in this project from different providers. You must have a valid key from all those providers to be able to run the `lampe-sdk` review:

- Anthropic
- OpenAI

1. **Get API Credentials:** Go to each platform create an account or signin, then get an API secret key.

2, **Store it in `.env`:** You will then need to create the following environment variable, so litellm can reach the provider for you.

- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

## GitHub Action

The Lampe SDK includes a GitHub Action that makes it easy to integrate PR description generation and code review into your GitHub workflows.

### Quick Start

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

### Features

- **Automatic Git History Fetching**: Includes merge-base functionality to ensure all PR commits are available
- **Multiple Commands**: Support for `describe`, `review`, and `healthcheck` commands
- **Flexible Configuration**: Extensive options for customization
- **Multiple Output Providers**: Support for console, GitHub, GitLab, and Bitbucket outputs
- **Two Generation Variants**: Default and agentic modes

### Advanced Usage

```yaml
name: Lampe Analysis
on:
  pull_request:

jobs:
  analyze:
    runs-on: ubuntu-latest
    env:
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      LAMPE_GITHUB_APP_ID: ${{ secrets.LAMPE_GITHUB_APP_ID }}
      LAMPE_GITHUB_APP_PRIVATE_KEY: ${{ secrets.LAMPE_GITHUB_APP_PRIVATE_KEY }}
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}

      # Health check
      - name: Health Check
        uses: montagne-dev/lampe@main
        with:
          command: healthcheck

      # Generate description
      - name: Generate Description
        uses: montagne-dev/lampe@main
        with:
          command: describe
          variant: agentic
          output: github
```

### Required Secrets

Set these in your repository settings:

- `OPENAI_API_KEY`: Your OpenAI API key
- `ANTHROPIC_API_KEY`: Your Anthropic API key (optional, for agentic mode)
- `LAMPE_GITHUB_APP_ID`: GitHub App ID (optional, for GitHub integration)
- `LAMPE_GITHUB_APP_PRIVATE_KEY`: GitHub App private key (optional, for GitHub integration)

For detailed documentation, see [Github action page](http://127.0.0.1:8000/github-actions/) in the documentation.

## Bitbucket Pipeline

https://support.atlassian.com/bitbucket-cloud/docs/pipeline-start-conditions/#Pull-Requests
