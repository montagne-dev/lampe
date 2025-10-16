from __future__ import annotations

import logging
import os
import sys

from lampe.cli.providers.github import GitHubProvider
from lampe.core import initialize
from lampe.core.data_models.pull_request import PullRequest
from lampe.core.data_models.repository import Repository
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)


def healthcheck() -> None:
    """Check if the CLI is healthy and can connect to GitHub."""
    logger.info("🔍 Checking CLI health...")
    initialize()
    # Check GitHub repository environment variable
    github_repo = os.getenv("GITHUB_REPOSITORY")
    if not github_repo or len(github_repo.split("/")) != 2:
        logger.info("❌ GITHUB_REPOSITORY environment variable not set")
        logger.info("   Set it to 'owner/repo' format (e.g., 'montagne-dev/lampe')")
        sys.exit(1)
    logger.info(f"✅ GITHUB_REPOSITORY set to: {github_repo}")

    # Check authentication environment variables
    app_id = os.getenv("LAMPE_GITHUB_APP_ID")
    private_key = os.getenv("LAMPE_GITHUB_APP_PRIVATE_KEY")
    token = os.getenv("LAMPE_GITHUB_TOKEN")

    auth_method = None
    if app_id and private_key:
        auth_method = "GitHub App"
        logger.info(f"✅ GitHub App authentication detected (App ID: {app_id})")
    elif token:
        auth_method = "User Token"
        logger.info("✅ User token authentication detected")
    else:
        logger.info("❌ No GitHub authentication found")
        logger.info("   Set either:")
        logger.info("   - LAMPE_GITHUB_APP_ID and LAMPE_GITHUB_APP_PRIVATE_KEY for GitHub App")
        logger.info("   - LAMPE_GITHUB_TOKEN for user token authentication")
        sys.exit(1)

    # Test GitHub connection
    try:
        # Create dummy repository and pull request objects for testing
        repo = Repository(local_path=".", full_name=github_repo)
        pr = PullRequest(
            number=1,
            title="Test PR",
            base_commit_hash="test-base",
            base_branch_name="main",
            head_commit_hash="test-head",
            head_branch_name="feature/test",
        )

        # Initialize GitHub provider to test authentication
        provider = GitHubProvider(repository=repo, pull_request=pr)
        logger.info(f"✅ GitHub {auth_method} authentication successful")

        # Test API access by getting repository info
        repo_info = provider.github_client.get_repo(github_repo)
        logger.info(f"✅ Repository access confirmed: {repo_info.full_name}")
        logger.info(f"   Description: {repo_info.description or 'No description'}")
        logger.info(f"   Private: {repo_info.private}")

        # Check LLM API keys
        logger.info("\n🔑 Checking LLM API keys...")
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
        logger.info(f"❌ GitHub connection failed: {e}")
        logger.info("\nTroubleshooting tips:")
        if auth_method == "GitHub App":
            logger.info("- Verify LAMPE_GITHUB_APP_ID and LAMPE_GITHUB_APP_PRIVATE_KEY are correct")
            logger.info("- Ensure the GitHub App is installed on the repository")
            logger.info("- Check that the private key is properly formatted")
        else:
            logger.info("- Verify LAMPE_GITHUB_TOKEN is valid and has appropriate permissions")
            logger.info("- Ensure the token has 'repo' scope for private repositories")
        sys.exit(1)
