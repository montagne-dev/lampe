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
  # Automatic pipeline for pull requests
  # WARNING: PR description is always generated from the full diff on every push (no optimizations yet).
  pull-requests:
    "**":
      - step:
          name: LampeCI
          script:
            # Debug: Show triggered variables
            - echo "BITBUCKET_PR_DESTINATION_BRANCH: $BITBUCKET_PR_DESTINATION_BRANCH"
            - echo "BITBUCKET_BRANCH: $BITBUCKET_BRANCH"
            - echo "BITBUCKET_COMMIT: $BITBUCKET_COMMIT"
            - echo "BITBUCKET_PR_TITLE: $BITBUCKET_PR_TITLE"

            # Install uv using the official installer
            - echo "Installing uv..."
            - curl -LsSf https://astral.sh/uv/install.sh | sh
            - export PATH="$HOME/.local/bin:$PATH"
            # Install Lampe using uv tool install
            - uv tool install git+https://github.com/montagne-dev/lampe.git@main
            - git fetch origin "+refs/heads/$BITBUCKET_PR_DESTINATION_BRANCH:refs/remotes/origin/$BITBUCKET_PR_DESTINATION_BRANCH"
            - git fetch origin "+refs/heads/$BITBUCKET_BRANCH:refs/remotes/origin/$BITBUCKET_BRANCH"
            - MERGE_BASE=$(git merge-base origin/$BITBUCKET_PR_DESTINATION_BRANCH origin/$BITBUCKET_BRANCH)
            - lampe healthcheck || (echo "Lampe CLI healthcheck failed" && exit 1)

            # Set environment variables
            - export OPENAI_API_KEY=$OPENAI_API_KEY
            - export ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
            - export LAMPE_BITBUCKET_TOKEN=$LAMPE_BITBUCKET_TOKEN
            # Or, for Bitbucket App auth:
            # - export LAMPE_BITBUCKET_APP_KEY=$LAMPE_BITBUCKET_APP_KEY
            # - export LAMPE_BITBUCKET_APP_SECRET=$LAMPE_BITBUCKET_APP_SECRET

            # Run Lampe with merge base and head commits
            - lampe describe --repo . --base $MERGE_BASE --head $BITBUCKET_COMMIT --title "$BITBUCKET_PR_TITLE" --output bitbucket

            # Optional: Run code review
            # - lampe review --repo . --base $MERGE_BASE --head $BITBUCKET_COMMIT --title "$BITBUCKET_PR_TITLE" --output bitbucket --review-depth standard
          services:
            - docker
```

## Review Only on PR Open

By default, Bitbucket Pipelines triggers on every push to a pull request branch. If you want to run code reviews only when a PR is first opened (and skip reviews on subsequent pushes), you can use one of the following approaches.

### Approach 1: Check for Existing Reviews (Recommended)

This approach checks if the token user (the account associated with `LAMPE_BITBUCKET_TOKEN`) has already commented on the PR. If the token user has commented, the review step is skipped. This is the most reliable method since it directly checks the PR state and works regardless of the review format or content.

```yaml
# bitbucket-pipelines.yml

image: python:3.12

pipelines:
  pull-requests:
    "**":
      - step:
          name: LampeCI
          script:
            # Install dependencies
            - echo "Installing uv..."
            - curl -LsSf https://astral.sh/uv/install.sh | sh
            - export PATH="$HOME/.local/bin:$PATH"
            - uv tool install git+https://github.com/montagne-dev/lampe.git@main

            # Install jq for JSON parsing
            - apt-get update && apt-get install -y jq curl

            # Fetch branches
            - git fetch origin "+refs/heads/$BITBUCKET_PR_DESTINATION_BRANCH:refs/remotes/origin/$BITBUCKET_PR_DESTINATION_BRANCH"
            - git fetch origin "+refs/heads/$BITBUCKET_BRANCH:refs/remotes/origin/$BITBUCKET_BRANCH"
            - MERGE_BASE=$(git merge-base origin/$BITBUCKET_PR_DESTINATION_BRANCH origin/$BITBUCKET_BRANCH)

            # Set environment variables
            - export OPENAI_API_KEY=$OPENAI_API_KEY
            - export ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
            - export LAMPE_BITBUCKET_TOKEN=$LAMPE_BITBUCKET_TOKEN

            # Always generate/update PR description
            - lampe describe --repo . --base $MERGE_BASE --head $BITBUCKET_COMMIT --title "$BITBUCKET_PR_TITLE" --output bitbucket

            # Check if review already exists and run review only on PR open
            - |
              echo "Checking if PR already has a review from the token user..."

              # Get the current authenticated user (token owner)
              AUTH_HEADER="Authorization: Bearer $LAMPE_BITBUCKET_TOKEN"
              USER_INFO=$(curl -s -H "$AUTH_HEADER" "https://api.bitbucket.org/2.0/user")
              TOKEN_USER_UUID=$(echo "$USER_INFO" | jq -r '.uuid // .account_id')

              if [ -z "$TOKEN_USER_UUID" ] || [ "$TOKEN_USER_UUID" = "null" ]; then
                echo "Warning: Could not determine token user. Proceeding with review..."
                TOKEN_USER_UUID=""
              else
                echo "Token user UUID: $TOKEN_USER_UUID"
              fi

              # Get PR comments and check if token user has already commented
              API_URL="https://api.bitbucket.org/2.0/repositories/$BITBUCKET_WORKSPACE/$BITBUCKET_REPO_SLUG/pullrequests/$BITBUCKET_PR_ID/comments"

              if [ -n "$TOKEN_USER_UUID" ]; then
                # Check for comments by the token user
                REVIEW_EXISTS=$(curl -s -H "$AUTH_HEADER" "$API_URL" | jq -r --arg uuid "$TOKEN_USER_UUID" '.values[] | select(.user.uuid == $uuid or .user.account_id == $uuid) | .id' | head -1)
              else
                # Fallback: check by username if UUID lookup failed
                TOKEN_USERNAME=$(echo "$USER_INFO" | jq -r '.username // .nickname')
                if [ -n "$TOKEN_USERNAME" ] && [ "$TOKEN_USERNAME" != "null" ]; then
                  echo "Token username: $TOKEN_USERNAME"
                  REVIEW_EXISTS=$(curl -s -H "$AUTH_HEADER" "$API_URL" | jq -r --arg username "$TOKEN_USERNAME" '.values[] | select(.user.username == $username or .user.nickname == $username) | .id' | head -1)
                fi
              fi

              if [ -n "$REVIEW_EXISTS" ]; then
                echo "Review already exists from token user (comment ID: $REVIEW_EXISTS). Skipping review."
              else
                echo "No existing review found from token user. Running review..."
                lampe review --repo . --base $MERGE_BASE --head $BITBUCKET_COMMIT --title "$BITBUCKET_PR_TITLE" --output bitbucket --review-depth standard
              fi
          services:
            - docker
```

### Approach 2: Check Commit Count (Alternative)

This approach checks if this is likely the first push to the PR by comparing the number of commits. This is less reliable but doesn't require API calls.

```yaml
# bitbucket-pipelines.yml

image: python:3.12

pipelines:
  pull-requests:
    "**":
      - step:
          name: LampeCI
          script:
            # Install dependencies
            - echo "Installing uv..."
            - curl -LsSf https://astral.sh/uv/install.sh | sh
            - export PATH="$HOME/.local/bin:$PATH"
            - uv tool install git+https://github.com/montagne-dev/lampe.git@main

            # Fetch branches
            - git fetch origin "+refs/heads/$BITBUCKET_PR_DESTINATION_BRANCH:refs/remotes/origin/$BITBUCKET_PR_DESTINATION_BRANCH"
            - git fetch origin "+refs/heads/$BITBUCKET_BRANCH:refs/remotes/origin/$BITBUCKET_BRANCH"
            - MERGE_BASE=$(git merge-base origin/$BITBUCKET_PR_DESTINATION_BRANCH origin/$BITBUCKET_BRANCH)

            # Set environment variables
            - export OPENAI_API_KEY=$OPENAI_API_KEY
            - export ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
            - export LAMPE_BITBUCKET_TOKEN=$LAMPE_BITBUCKET_TOKEN

            # Always generate/update PR description
            - lampe describe --repo . --base $MERGE_BASE --head $BITBUCKET_COMMIT --title "$BITBUCKET_PR_TITLE" --output bitbucket

            # Check if this is the first commit in PR and run review only on PR open
            - |
              echo "Checking if this is the first push to the PR..."

              # Count commits between merge base and head
              COMMIT_COUNT=$(git rev-list --count $MERGE_BASE..$BITBUCKET_COMMIT)
              echo "Commit count since merge base: $COMMIT_COUNT"

              # Check if merge base equals destination branch HEAD (likely first push)
              DEST_HEAD=$(git rev-parse origin/$BITBUCKET_PR_DESTINATION_BRANCH)

              if [ "$MERGE_BASE" = "$DEST_HEAD" ] && [ "$COMMIT_COUNT" -le 5 ]; then
                echo "Likely first push to PR. Running review..."
                lampe review --repo . --base $MERGE_BASE --head $BITBUCKET_COMMIT --title "$BITBUCKET_PR_TITLE" --output bitbucket --review-depth standard
              else
                echo "PR has been updated. Skipping review to avoid redundancy."
              fi
          services:
            - docker
```

### Approach 3: Separate Steps with Conditions

You can also separate description generation and review into different steps, with the review step conditionally skipped:

```yaml
# bitbucket-pipelines.yml

image: python:3.12

pipelines:
  pull-requests:
    "**":
      # Step 1: Always generate/update PR description
      - step:
          name: Generate PR Description
          script:
            - curl -LsSf https://astral.sh/uv/install.sh | sh
            - export PATH="$HOME/.local/bin:$PATH"
            - uv tool install git+https://github.com/montagne-dev/lampe.git@main
            - git fetch origin "+refs/heads/$BITBUCKET_PR_DESTINATION_BRANCH:refs/remotes/origin/$BITBUCKET_PR_DESTINATION_BRANCH"
            - git fetch origin "+refs/heads/$BITBUCKET_BRANCH:refs/remotes/origin/$BITBUCKET_BRANCH"
            - MERGE_BASE=$(git merge-base origin/$BITBUCKET_PR_DESTINATION_BRANCH origin/$BITBUCKET_BRANCH)
            - export OPENAI_API_KEY=$OPENAI_API_KEY
            - export ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
            - export LAMPE_BITBUCKET_TOKEN=$LAMPE_BITBUCKET_TOKEN
            - lampe describe --repo . --base $MERGE_BASE --head $BITBUCKET_COMMIT --title "$BITBUCKET_PR_TITLE" --output bitbucket

      # Step 2: Review only if no review exists
      - step:
          name: Code Review (PR Open Only)
          script:
            - curl -LsSf https://astral.sh/uv/install.sh | sh
            - export PATH="$HOME/.local/bin:$PATH"
            - uv tool install git+https://github.com/montagne-dev/lampe.git@main
            - apt-get update && apt-get install -y jq curl
            - git fetch origin "+refs/heads/$BITBUCKET_PR_DESTINATION_BRANCH:refs/remotes/origin/$BITBUCKET_PR_DESTINATION_BRANCH"
            - git fetch origin "+refs/heads/$BITBUCKET_BRANCH:refs/remotes/origin/$BITBUCKET_BRANCH"
            - MERGE_BASE=$(git merge-base origin/$BITBUCKET_PR_DESTINATION_BRANCH origin/$BITBUCKET_BRANCH)
            - export OPENAI_API_KEY=$OPENAI_API_KEY
            - export ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
            - export LAMPE_BITBUCKET_TOKEN=$LAMPE_BITBUCKET_TOKEN
            - |
              echo "Checking if PR already has a review from the token user..."

              # Get the current authenticated user (token owner)
              AUTH_HEADER="Authorization: Bearer $LAMPE_BITBUCKET_TOKEN"
              USER_INFO=$(curl -s -H "$AUTH_HEADER" "https://api.bitbucket.org/2.0/user")
              TOKEN_USER_UUID=$(echo "$USER_INFO" | jq -r '.uuid // .account_id')

              if [ -z "$TOKEN_USER_UUID" ] || [ "$TOKEN_USER_UUID" = "null" ]; then
                echo "Warning: Could not determine token user. Proceeding with review..."
                TOKEN_USER_UUID=""
              else
                echo "Token user UUID: $TOKEN_USER_UUID"
              fi

              # Get PR comments and check if token user has already commented
              API_URL="https://api.bitbucket.org/2.0/repositories/$BITBUCKET_WORKSPACE/$BITBUCKET_REPO_SLUG/pullrequests/$BITBUCKET_PR_ID/comments"

              if [ -n "$TOKEN_USER_UUID" ]; then
                # Check for comments by the token user
                REVIEW_EXISTS=$(curl -s -H "$AUTH_HEADER" "$API_URL" | jq -r --arg uuid "$TOKEN_USER_UUID" '.values[] | select(.user.uuid == $uuid or .user.account_id == $uuid) | .id' | head -1)
              else
                # Fallback: check by username if UUID lookup failed
                TOKEN_USERNAME=$(echo "$USER_INFO" | jq -r '.username // .nickname')
                if [ -n "$TOKEN_USERNAME" ] && [ "$TOKEN_USERNAME" != "null" ]; then
                  echo "Token username: $TOKEN_USERNAME"
                  REVIEW_EXISTS=$(curl -s -H "$AUTH_HEADER" "$API_URL" | jq -r --arg username "$TOKEN_USERNAME" '.values[] | select(.user.username == $username or .user.nickname == $username) | .id' | head -1)
                fi
              fi

              if [ -n "$REVIEW_EXISTS" ]; then
                echo "Review already exists from token user (comment ID: $REVIEW_EXISTS). Exiting step."
                exit 0
              fi

              echo "No existing review found from token user. Proceeding with review..."
            - lampe review --repo . --base $MERGE_BASE --head $BITBUCKET_COMMIT --title "$BITBUCKET_PR_TITLE" --output bitbucket --review-depth standard
          services:
            - docker
```

### Choosing the Right Approach

**Use Approach 1 (Check for Existing Reviews)** when:

- You want the most reliable detection (checks by token user, not content)
- You don't mind extra API calls (one to get user info, one to check comments)
- You want to ensure no duplicate reviews from the same token user

**Use Approach 2 (Check Commit Count)** when:

- You want to avoid API calls
- You're okay with a heuristic-based approach
- Performance is a concern

**Use Approach 3 (Separate Steps)** when:

- You want clear separation of concerns
- You want to see review step status in the pipeline UI
- You want to easily enable/disable review step

### Important Notes

1. **API Rate Limits**: Approach 1 makes two API calls to Bitbucket (one to get the token user info, one to check PR comments). Ensure your token has sufficient rate limits.

2. **Review Detection**: The review detection checks if the token user (the account associated with `LAMPE_BITBUCKET_TOKEN`) has already commented on the PR. This is more reliable than searching for specific strings and works regardless of the review format.

3. **Description vs Review**: PR descriptions are always generated/updated on every push, while reviews only run on PR open. This allows descriptions to stay current while avoiding redundant reviews.

4. **Manual Re-review**: If you need to re-run a review after changes, you can use the manual pipeline trigger or delete the existing review comment.

## Manual Pipeline Triggers

You can also configure Lampe to run only when manually triggered. This is useful for on-demand PR description generation or when you want to control when the analysis runs.

### Why Use Manual Pipelines?

Manual pipelines provide several advantages over automatic PR description generation, and there are important technical limitations in Bitbucket Pipelines that make manual pipelines necessary for certain use cases.

#### 1. **Bitbucket Pipeline Limitations with Commit Ranges**

**The Problem**: Bitbucket Pipelines has a fundamental limitation when it comes to detecting commit ranges in pull request events. According to the [Atlassian Community](https://community.atlassian.com/forums/Bitbucket-questions/getting-last-commit-before-push-of-a-specific-build/qaq-p/671528), when a user accumulates multiple local commits before pushing to the origin, `BITBUCKET_COMMIT` only points to the last commit, not the range of commits that triggered the build.

This limitation is also documented in [Bitbucket's official pipeline start conditions documentation](https://support.atlassian.com/bitbucket-cloud/docs/pipeline-start-conditions/#Pull-Requests), which explains how pull request pipelines work and their inherent limitations with commit range detection.

**Why This Matters**: For accurate PR description generation, you need to know:

- What commits were actually pushed (not just the latest one)
- The range of changes between the base and head commits
- Which specific commits are new in this push

**The Solution**: Manual pipelines allow you to specify exact commit ranges using `BASE_COMMIT` and `HEAD_COMMIT` variables, giving you precise control over what gets analyzed.

#### 2. **Selective Processing**

If you prefer to manually generate PR descriptions for specific pull requests rather than automatically processing every push, manual pipelines give you full control over when and which PRs to analyze.

#### 3. **Iterative Description Generation**

Manual pipelines allow you to specify two specific commits to compare, enabling iterative PR description generation. This is particularly powerful for:

- **Incremental Updates**: Generate descriptions based on specific commit ranges
- **Review-focused Analysis**: Focus on the latest changes since the last review
- **Custom Comparison Points**: Compare any two commits, not just the merge base

#### 4. **Future-Proofing for Advanced Features**

The manual pipeline design prepares for upcoming CLI features that will enable:

- **Incremental Description Updates**: Compute new descriptions using existing descriptions and new diff changes
- **Review-based Analysis**: Generate descriptions that focus only on changes since the last review
- **Smart Diff Processing**: More intelligent analysis of what has actually changed

#### 5. **Flexible Workflow Integration**

Manual pipelines integrate better with:

- **Code Review Workflows**: Generate descriptions at specific review checkpoints
- **Feature Branch Management**: Process descriptions for specific feature milestones
- **Quality Gates**: Generate descriptions only when certain conditions are met

### When to Use Each Approach

**Use Automatic Pipelines when:**

- You want PR descriptions generated automatically on every push
- You're comfortable with full codebase analysis on each change
- You prefer a "set and forget" approach

**Use Manual Pipelines when:**

- You want control over which PRs get processed
- You need to analyze specific commit ranges
- You're preparing for advanced iterative features
- You want to integrate with custom review workflows

### Manual Pipeline Configuration

```yaml
# bitbucket-pipelines.yml

image: python:3.12

pipelines:
  # Manual pipeline - only runs when triggered manually
  manual:
    generate-pr-description:
      - variables:
          - name: TARGET_BRANCH
            default: main
          - name: PR_NUMBER
          - name: BASE_COMMIT
          - name: HEAD_COMMIT
      - step:
          name: Manual LampeCI
          script:
            # Install uv using the official installer
            - curl -LsSf https://astral.sh/uv/install.sh | sh
            - export PATH="$HOME/.local/bin:$PATH"
            # Install Lampe using uv tool install
            - uv tool install git+https://github.com/montagne-dev/lampe.git@main

            # Set default values if not provided
            - |
              BASE_COMMIT=${BASE_COMMIT:-$TARGET_BRANCH}
              HEAD_COMMIT=${HEAD_COMMIT:-$BITBUCKET_BRANCH}

              # Validate that we have values
              if [ -z "$BASE_COMMIT" ]; then
                echo "ERROR: BASE_COMMIT is empty after resolution"
                exit 1
              fi

              if [ -z "$HEAD_COMMIT" ]; then
                echo "ERROR: HEAD_COMMIT is empty after resolution"
                exit 1
              fi

            # Handle BASE_COMMIT and HEAD_COMMIT
            - |
              # If BASE_COMMIT is set, it's a commit SHA - use it directly
              if [ -n "$BASE_COMMIT" ]; then
                echo "BASE_COMMIT is set (commit SHA): $BASE_COMMIT"
                BASE_SHA="$BASE_COMMIT"
              else
                # If not set, use TARGET_BRANCH and fetch it
                echo "BASE_COMMIT not set, using TARGET_BRANCH: $TARGET_BRANCH"
                echo "Fetching target branch: $TARGET_BRANCH"
                git fetch origin "+refs/heads/$TARGET_BRANCH:refs/remotes/origin/$TARGET_BRANCH"
                BASE_SHA=$(git rev-parse origin/$TARGET_BRANCH)
                echo "Base commit SHA: $BASE_SHA"
              fi

            - |
              # If HEAD_COMMIT is set, it's a commit SHA - use it directly
              if [ -n "$HEAD_COMMIT" ]; then
                echo "HEAD_COMMIT is set (commit SHA): $HEAD_COMMIT"
                HEAD_SHA="$HEAD_COMMIT"
              else
                # If not set, use current branch and fetch it
                echo "HEAD_COMMIT not set, using current branch: $BITBUCKET_BRANCH"
                echo "Fetching current branch: $BITBUCKET_BRANCH"
                git fetch origin "+refs/heads/$BITBUCKET_BRANCH:refs/remotes/origin/$BITBUCKET_BRANCH"
                HEAD_SHA=$(git rev-parse origin/$BITBUCKET_BRANCH)
                echo "Head commit SHA: $HEAD_SHA"
              fi

            # Calculate merge base using commit SHAs
            - |
              echo "Calculating merge base between $BASE_SHA and $HEAD_SHA"
              MERGE_BASE=$(git merge-base $BASE_SHA $HEAD_SHA)
              echo "Merge base: $MERGE_BASE"

            # Run healthcheck
            - lampe healthcheck || (echo "Lampe CLI healthcheck failed" && exit 1)

            # Set environment variables
            - export OPENAI_API_KEY=$OPENAI_API_KEY
            - export ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
            - export LAMPE_BITBUCKET_TOKEN=$LAMPE_BITBUCKET_TOKEN
            - export TARGET_BRANCH=$TARGET_BRANCH
            - export PR_NUMBER=$PR_NUMBER

            # Generate PR description
            - lampe describe --repo . --base $MERGE_BASE --head $HEAD_SHA --output bitbucket

            # Optional: Generate code review
            # - lampe review --repo . --base $MERGE_BASE --head $HEAD_SHA --output bitbucket --review-depth standard
          services:
            - docker
```

### Important: Variable Differences in Manual Triggers

When manually triggering a pipeline, **some variables are NOT available** because there's no pull request context. This is a fundamental limitation of Bitbucket Pipelines' manual trigger system.

#### Why PR Variables Are Not Available in Manual Triggers

According to [Atlassian's official documentation](https://support.atlassian.com/bitbucket-cloud/kb/how-do-i-manually-trigger-a-pull-requests-pipeline-on-a-pr/), manual pipelines run on branches, not on pull requests. The **Run Pipeline** dialog doesn't allow you to select a specific PR when triggering a pipeline manually because:

1. **No PR Context**: Manual triggers are branch-based, not PR-based
2. **Pipeline Type Mismatch**: Manual pipelines are designed for branch operations, not PR operations
3. **Variable Scope**: PR-specific variables (`BITBUCKET_PR_*`) are only available when pipelines are triggered by actual PR events

This is why manual pipelines require you to manually specify the PR number and other details through custom variables.

**Note**: There is an [active feature request (BCLOUD-23152)](https://support.atlassian.com/bitbucket-cloud/kb/how-do-i-manually-trigger-a-pull-requests-pipeline-on-a-pr/) to allow manually triggering pull-request pipelines from the UI for a specific PR, but this feature is not yet available.

#### ❌ NOT Available in Manual Triggers:

- `BITBUCKET_PR_ID` - No active PR context
- `BITBUCKET_PR_TITLE` - No active PR context
- `BITBUCKET_PR_DESTINATION_BRANCH` - No active PR context
- `BITBUCKET_PR_SOURCE_BRANCH` - No active PR context

#### ✅ Available in Manual Triggers:

- `BITBUCKET_COMMIT` - Current commit hash
- `BITBUCKET_BRANCH` - Current branch name
- `BITBUCKET_WORKSPACE` - Workspace slug
- `BITBUCKET_REPO_SLUG` - Repository slug

#### 🔧 Custom Variables for Manual Triggers:

The manual pipeline requires the following variables:

**Required:**

- `PR_NUMBER` - The pull request number to process
- `TARGET_BRANCH` - Target branch (defaults to `main`)

**Optional (with defaults):**

- `BASE_COMMIT` - Base commit to compare against (defaults to `TARGET_BRANCH`)
- `HEAD_COMMIT` - Head commit to analyze (defaults to current branch)

### How to Trigger Manual Pipelines

When you trigger the manual pipeline, Bitbucket will prompt you to enter the following variables:

#### Required Variables:

- **`PR_NUMBER`**: Enter the pull request number you want to process (e.g., `123`)

#### Optional Variables:

- **`TARGET_BRANCH`**: The target branch (defaults to `main` if not specified)
- **`BASE_COMMIT`**: Specific base commit hash (defaults to `TARGET_BRANCH` if not specified)
- **`HEAD_COMMIT`**: Specific head commit hash (defaults to current branch if not specified)

#### Triggering the Pipeline:

##### 1. **From the Branches view:**

- Go to your repository in Bitbucket
- Navigate to **Branches**
- Click the **⋯** (three dots) next to your branch
- Select **Run pipeline for a branch**
- Choose the `generate-pr-description` pipeline
- Fill in the required `PR_NUMBER` and any optional variables
- Click **Run**

##### 2. **From the Commits view:**

- Go to **Commits** in your repository
- Click on a specific commit
- Select **Run pipeline**
- Choose the `generate-pr-description` pipeline
- Fill in the required `PR_NUMBER` and any optional variables
- Click **Run**

##### 3. **From the Pipelines page:**

- Go to **Pipelines** in your repository
- Click **Run pipeline**
- Select your branch and the `generate-pr-description` pipeline
- Fill in the required `PR_NUMBER` and any optional variables
- Click **Run**

#### Example Usage:

**Basic usage (minimal required input):**

- `PR_NUMBER`: `123`
- `TARGET_BRANCH`: `main` (default)
- `BASE_COMMIT`: (leave empty, uses `main`)
- `HEAD_COMMIT`: (leave empty, uses current branch)

**Advanced usage (custom commits):**

- `PR_NUMBER`: `123`
- `TARGET_BRANCH`: `develop`
- `BASE_COMMIT`: `abc123def456` (specific commit hash)
- `HEAD_COMMIT`: `def456ghi789` (specific commit hash)

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
- `lampe review` - Generate code reviews
- `lampe healthcheck` - Validate setup

### Review Command

The `lampe review` command supports automatic model selection based on review depth:

**Review Depth Options:**

- **`basic`**: Uses `gpt-5-nano` for faster, lighter reviews
- **`standard`**: Uses `gpt-5` for balanced reviews (default)
- **`comprehensive`**: Uses `gpt-5.1` for thorough, detailed reviews

**Example with review command:**

```yaml
# Generate code review with standard depth
- lampe review --repo . --base $MERGE_BASE --head $BITBUCKET_COMMIT --title "$BITBUCKET_PR_TITLE" --output bitbucket --review-depth standard

# Generate comprehensive review
- lampe review --repo . --base $MERGE_BASE --head $BITBUCKET_COMMIT --title "$BITBUCKET_PR_TITLE" --output bitbucket --review-depth comprehensive

# Quick review with basic depth
- lampe review --repo . --base $MERGE_BASE --head $BITBUCKET_COMMIT --title "$BITBUCKET_PR_TITLE" --output bitbucket --review-depth basic --variant diff-by-diff
```

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

### Common Issues

#### "fatal: Not a valid object name" Error

This error occurs when Git cannot find the specified branch or commit reference. The `git merge-base` command works with both branch names and commit hashes, but the issue is usually that the references haven't been fetched properly.

If you encounter this error:
**Check fetch success**: Ensure the `git fetch` commands completed successfully and created proper local references:

```bash
   git fetch origin "+refs/heads/$BASE_COMMIT:refs/remotes/origin/$BASE_COMMIT"
   git fetch origin "+refs/heads/$HEAD_COMMIT:refs/remotes/origin/$HEAD_COMMIT"
```

**Important**: We use `refs/remotes/origin/` instead of `refs/heads/` to avoid conflicts with checked-out branches. Then use `origin/$BRANCH` in `git merge-base` commands.

#### Git Merge Base Failures Due to Shallow Clones

**Root Cause**: The most common cause of `git merge-base` failures in Bitbucket Pipelines is using `--depth=1` in git fetch commands. This creates a shallow clone with only the latest commit, which doesn't provide enough history for merge base calculation.

**Solution**: Remove `--depth=1` from git fetch commands to allow full history access:

```bash
# ❌ WRONG - This will cause merge-base to fail
git fetch --depth=1 origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"

# ✅ CORRECT - This allows merge-base to work
git fetch origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
```

**Why this happens**: `git merge-base` needs to traverse commit history to find the common ancestor between two branches. With `--depth=1`, only the latest commit is available, making it impossible to calculate the merge base.

**Alternative**: If you need to limit fetch depth for performance reasons, use a larger depth value that includes the merge base:

```bash
# Fetch enough history to include the merge base
git fetch --depth=50 origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
```

**Verify branch existence**: Make sure the branches exist in the remote repository:

```bash
git ls-remote origin | grep <branch-name>
```

**Check available references**: The pipeline will show available branches and refs if the merge base calculation fails, helping you debug the issue.

**Use commit hashes if needed**: If branch names continue to fail, you can use specific commit hashes:

- `BASE_COMMIT`: `abc123def456` (specific commit hash)
- `HEAD_COMMIT`: `def456ghi789` (specific commit hash)

#### Merge Base Calculation Failures

If the merge base calculation fails:

1. **Check commit validity**: Ensure both commits exist and are accessible
2. **Verify repository state**: Make sure the repository is in a clean state
3. **Check fetch success**: Ensure the `git fetch` commands completed success1y

#### Manual Pipeline Variables

When using manual pipelines, remember:

- **Branch names vs commit hashes**: The pipeline handles both, but commit hashes are more reliable
- **Default values**: If you don't specify `BASE_COMMIT` or `HEAD_COMMIT`, they default to `TARGET_BRANCH` and current branch respectively
- **Variable validation**: The pipeline validates that the specified commits/branches exist before proceeding
