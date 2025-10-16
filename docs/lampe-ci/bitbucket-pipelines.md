# Bitbucket Pipelines Integration

## Overview

The lampe-sdk supports Bitbucket Pipelines for automated PR description generation. This integration provides similar functionality to GitHub Actions but optimized for Bitbucket's pipeline system.

## Features

- **Automatic PR Analysis**: Generate descriptions for pull requests
- **Multiple Authentication Methods**: Support for both token and app password authentication
- **Environment Detection**: Automatic provider detection in Bitbucket Pipelines
- **Fallback Support**: Console output when API calls fail

## Pipeline Configuration

```yaml
# bitbucket-pipelines.yml

image: python:3.12

pipelines:
  pull-requests:
    "**":
      - step:
          name: LampeCI

          script:
            # Install Lampe CLI
            - pip install git+https://github.com/montagne-dev/lampe.git

            # Fetch merge base and head commits
            - echo "Fetching merge base and head commits..."
            - git fetch --depth=1 origin $BITBUCKET_PR_DESTINATION_BRANCH
            - git fetch --depth=1 origin $BITBUCKET_BRANCH

            # Calculate merge base
            - MERGE_BASE=$(git merge-base $BITBUCKET_PR_DESTINATION_BRANCH $BITBUCKET_BRANCH)

            # Optional: Run a healthcheck using Lampe CLI to verify connectivity to LLMs and Bitbucket
            - lampe healthcheck || (echo "Lampe CLI healthcheck failed" && exit 1)

            # Run Lampe with merge base and head commits
            - lampe describe --repo . --base $MERGE_BASE --head $BITBUCKET_COMMIT --title "$BITBUCKET_PR_TITLE" --output bitbucket
          services:
            - docker
          env:
            # Required LLM API keys
            - OPENAI_API_KEY: $OPENAI_API_KEY
            - ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
            # Bitbucket authentication (choose one)
            - LAMPE_BITBUCKET_TOKEN: $LAMPE_BITBUCKET_TOKEN
            # OR for Bitbucket App authentication:
            # - LAMPE_BITBUCKET_APP_KEY: $LAMPE_BITBUCKET_APP_KEY
            # - LAMPE_BITBUCKET_APP_SECRET: $LAMPE_BITBUCKET_APP_SECRET
```

## Environment Variables

### Required Variables

| Variable            | Description       | Required               |
| ------------------- | ----------------- | ---------------------- |
| `OPENAI_API_KEY`    | OpenAI API key    | Yes                    |
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes (for agentic mode) |

### Bitbucket Authentication (Choose One)

#### Option 1: Repository/Workspace Access Token (Recommended)

| Variable                | Description            | Required |
| ----------------------- | ---------------------- | -------- |
| `LAMPE_BITBUCKET_TOKEN` | Bitbucket access token | Yes      |

#### Option 2: Bitbucket App (Fallback)

| Variable                     | Description          | Required |
| ---------------------------- | -------------------- | -------- |
| `LAMPE_BITBUCKET_APP_KEY`    | Bitbucket App Key    | Yes      |
| `LAMPE_BITBUCKET_APP_SECRET` | Bitbucket App Secret | Yes      |

### Bitbucket Pipelines Variables (Auto-provided)

| Variable              | Description     | Required            |
| --------------------- | --------------- | ------------------- |
| `BITBUCKET_WORKSPACE` | Workspace slug  | Auto (in pipelines) |
| `BITBUCKET_REPO_SLUG` | Repository slug | Auto (in pipelines) |
| `BITBUCKET_PR_ID`     | Pull request ID | Auto (in pipelines) |

## Commands

- `lampe describe` - Generate PR descriptions
- `lampe healthcheck` - Validate setup

## Output Providers

- `bitbucket` - Native Bitbucket PR description updates
- `console` - Console output for debugging
- `auto` - Automatic provider detection

## Setup Instructions

### 1. Create Bitbucket Access Token (Recommended)

1. Go to your Bitbucket account settings
2. Navigate to "App passwords" or "Access tokens"
3. Create a new token with repository read/write permissions
4. Add the token as a repository variable: `LAMPE_BITBUCKET_TOKEN`

### 2. Alternative: Bitbucket App Setup

1. Go to your Bitbucket account settings
2. Navigate to "OAuth consumers" or "Apps"
3. Create a new OAuth consumer with the following permissions:
   - Repositories: Read, Write
   - Pull requests: Read, Write
4. Add the app credentials as repository variables:
   - `LAMPE_BITBUCKET_APP_KEY` (the OAuth consumer key)
   - `LAMPE_BITBUCKET_APP_SECRET` (the OAuth consumer secret)

### 3. Configure Pipeline

Add the pipeline configuration to your `bitbucket-pipelines.yml` file as shown above.

## Troubleshooting

- **Authentication errors**: Verify your token or app credentials have repository permissions
- **Environment variables**: Ensure all required variables are set in repository settings
- **OAuth App setup**: Make sure your Bitbucket App has the correct permissions (Repositories: Read/Write, Pull requests: Read/Write)
- **Fallback behavior**: If API calls fail, descriptions will be logged to console
