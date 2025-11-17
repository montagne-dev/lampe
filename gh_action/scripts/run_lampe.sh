#!/bin/bash

# Lampe CLI runner script for GitHub Actions

set -e

echo "🔦 Running Lampe CLI..."
echo "Command: $COMMAND"
echo "Repository: $REPO"
echo "Title: $TITLE"
echo "Base ref: $BASE_REF"
echo "Head ref: $HEAD_REF"
echo "Output: $OUTPUT"
echo "Variant: $VARIANT"
echo "Review Depth: ${REVIEW_DEPTH:-standard} (Model: basic=gpt-5-nano, standard=gpt-5, comprehensive=gpt-5.1)"

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Install Lampe CLI if not already available
if ! command -v lampe &> /dev/null; then
    echo "Lampe CLI not found, installing from source..."
    uv tool install git+https://github.com/montagne-dev/lampe.git@feat/code-review-diff-by-diff
else
    echo "Lampe CLI is already available."
fi

# Helper functions for reusable argument building
add_file_exclusions() {
    if [ -n "$FILES_EXCLUDE" ]; then
        IFS=',' read -ra EXCLUDE_ARRAY <<< "$FILES_EXCLUDE"
        for pattern in "${EXCLUDE_ARRAY[@]}"; do
            LAMPE_ARGS+=("--exclude" "$pattern")
        done
    fi
}

add_file_reinclusions() {
    if [ -n "$FILES_REINCLUDE" ]; then
        IFS=',' read -ra REINCLUDE_ARRAY <<< "$FILES_REINCLUDE"
        for pattern in "${REINCLUDE_ARRAY[@]}"; do
            LAMPE_ARGS+=("--reinclude" "$pattern")
        done
    fi
}

add_common_arguments() {
    LAMPE_ARGS+=("--repo" "$REPO")
    LAMPE_ARGS+=("--title" "$TITLE")
    LAMPE_ARGS+=("--base" "$BASE_REF")
    LAMPE_ARGS+=("--head" "$HEAD_REF")
    LAMPE_ARGS+=("--output" "$OUTPUT")
    LAMPE_ARGS+=("--variant" "$VARIANT")


    # Add file filtering arguments
    add_file_exclusions
    add_file_reinclusions

    # Add optional arguments if provided
    if [ -n "$TIMEOUT_SECONDS" ]; then
        LAMPE_ARGS+=("--timeout-seconds" "$TIMEOUT_SECONDS")
    fi

    if [ "$VERBOSE" = "true" ]; then
        LAMPE_ARGS+=("--verbose")
    fi
}

# Build the command arguments
LAMPE_ARGS=()

# Add command-specific arguments based on the command
case "$COMMAND" in
    "describe")
        LAMPE_ARGS+=("describe")
        add_common_arguments
        if [ -n "$MAX_TOKENS" ]; then
            LAMPE_ARGS+=("--max-tokens" "$MAX_TOKENS")
        fi
        ;;

    "review")
        LAMPE_ARGS+=("review")
        add_common_arguments
        if [ -n "$REVIEW_DEPTH" ]; then
            LAMPE_ARGS+=("--review-depth" "$REVIEW_DEPTH")
        fi
        ;;

    "healthcheck")
        LAMPE_ARGS+=("healthcheck")
        ;;

    *)
        echo "❌ Unknown command: $COMMAND"
        echo "Available commands: describe, review, healthcheck"
        exit 1
        ;;
esac

# Run the command
echo "Executing: lampe ${LAMPE_ARGS[*]}"
lampe "${LAMPE_ARGS[@]}"

echo "✅ Lampe CLI completed successfully!"
