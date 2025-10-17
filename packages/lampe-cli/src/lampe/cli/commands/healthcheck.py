from __future__ import annotations

import logging
import os
import sys

from lampe.cli.providers.base import Provider
from lampe.core import initialize
from lampe.core.data_models.pull_request import PullRequest
from lampe.core.data_models.repository import Repository
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)


def healthcheck() -> None:
    """Check if the CLI is healthy and can connect to the configured provider."""
    logger.info("🔍 Checking CLI health...")
    initialize()
    # Create dummy repository and pull request objects for testing
    repo = Repository(local_path=".", full_name="test/repo")
    pr = PullRequest(
        number=1,
        title="Test PR",
        base_commit_hash="test-base",
        base_branch_name="main",
        head_commit_hash="test-head",
        head_branch_name="feature/test",
    )

    # Initialize provider and run healthcheck
    try:
        provider: Provider = Provider.create_provider("auto", repository=repo, pull_request=pr)
        provider.healthcheck()

        # Check LLM API keys
        logger.info("🔑 Checking LLM API keys...")
        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")

        if not openai_key and not anthropic_key:
            logger.info("❌ No LLM API keys found")
            logger.info("   Set at least one of:")
            logger.info("   - OPENAI_API_KEY for OpenAI models")
            logger.info("   - ANTHROPIC_API_KEY for Anthropic models")
            sys.exit(1)

        if openai_key:
            logger.info("✅ OPENAI_API_KEY is set")
        if anthropic_key:
            logger.info("✅ ANTHROPIC_API_KEY is set")

        logger.info("\n🎉 All health checks passed! CLI is ready to use.")

    except Exception as e:
        logger.exception(f"❌ Health check failed: {e}")
        sys.exit(1)
