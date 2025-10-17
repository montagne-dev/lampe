from __future__ import annotations

import logging
import os

from github import Auth, Github, GithubIntegration

from lampe.cli.providers.base import PRDescriptionPayload, Provider, update_or_add_text_between_tags
from lampe.core.data_models.pull_request import PullRequest
from lampe.core.data_models.repository import Repository
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)


class GitHubProvider(Provider):
    """GitHub provider for delivering PR descriptions to GitHub API."""

    def __init__(self, repository: Repository, pull_request: PullRequest) -> None:
        if pull_request.number == 0:
            pr_number = os.getenv("PR_NUMBER")
            if not pr_number:
                raise ValueError("PR_NUMBER environment variable is required for GitHub provider")
            pull_request.number = int(pr_number)

        super().__init__(repository, pull_request)

        # github action has many default environment variables, including the repository full name:
        # https://docs.github.com/en/actions/reference/workflows-and-actions/variables#default-environment-variables
        if repo_name := os.getenv("GITHUB_REPOSITORY"):
            self.owner, self.repo_name = repo_name.split("/")
        else:
            raise ValueError("GITHUB_REPOSITORY environment variable is required for GitHub provider")

        # Initialize GitHub client with appropriate authentication
        self.github_client = self._initialize_github_client()

    def _initialize_github_client(self) -> Github:
        """Initialize GitHub client with appropriate authentication method."""
        # Check for GitHub App authentication first
        app_id = os.getenv("LAMPE_GITHUB_APP_ID")
        private_key = os.getenv("LAMPE_GITHUB_APP_PRIVATE_KEY")

        if app_id and private_key:
            return self._create_github_app_client(app_id, private_key)

        # Fallback to user token authentication
        token = os.getenv("LAMPE_GITHUB_TOKEN")
        if not token:
            raise ValueError(
                "Either GitHub App credentials (LAMPE_GITHUB_APP_ID, LAMPE_GITHUB_APP_PRIVATE_KEY) "
                "or user token (LAMPE_GITHUB_TOKEN) environment variables are required for GitHub provider"
            )

        return self._create_user_token_client(token)

    def _create_github_app_client(self, app_id: str, private_key: str) -> Github:
        """Create GitHub client using GitHub App authentication."""
        try:
            auth = Auth.AppAuth(int(app_id), private_key)
            gi = GithubIntegration(auth=auth)
            # Use the owner and repo_name from environment variables
            installation = gi.get_repo_installation(self.owner, self.repo_name)
            return installation.get_github_for_installation()
        except Exception as e:
            raise ValueError(f"Failed to authenticate with GitHub App: {e}")

    def _create_user_token_client(self, token: str) -> Github:
        """Create GitHub client using user token authentication."""
        try:
            auth = Auth.Token(token)
            return Github(auth=auth)
        except Exception as e:
            raise ValueError(f"Failed to authenticate with GitHub token: {e}")

    def healthcheck(self) -> None:
        """Check if the GitHub provider is healthy and can connect to GitHub."""
        logger.info("🔍 Checking GitHub provider health...")

        # Check GitHub repository environment variable
        github_repo = os.getenv("GITHUB_REPOSITORY")
        if not github_repo or len(github_repo.split("/")) != 2:
            logger.info("❌ GITHUB_REPOSITORY environment variable not set")
            logger.info("   Set it to 'owner/repo' format (e.g., 'montagne-dev/lampe')")
            raise ValueError("GITHUB_REPOSITORY environment variable not set")
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
            raise ValueError("No GitHub authentication found")

        # Test GitHub connection
        try:
            # Test API access by getting repository info
            repo_info = self.github_client.get_repo(github_repo)
            logger.info(f"✅ Repository access confirmed: {repo_info.full_name}")
            logger.info(f"   Description: {repo_info.description or 'No description'}")
            logger.info(f"   Private: {repo_info.private}")
            logger.info(f"✅ GitHub {auth_method} authentication successful")

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
            raise

    def deliver_pr_description(self, payload: PRDescriptionPayload) -> None:
        """Update the PR description on GitHub."""
        if self.pull_request.number == 0:
            raise ValueError("Cannot update GitHub PR description for local run")

        try:
            repo = self.github_client.get_repo(f"{self.owner}/{self.repo_name}")
            pull_request = repo.get_pull(self.pull_request.number)
            new_description = update_or_add_text_between_tags(
                pull_request.body or "", payload.description_with_title, "description"
            )
            pull_request.edit(body=new_description)
            logger.info(f"✅ Successfully updated PR #{self.pull_request.number} description on GitHub")
        except Exception as e:
            logger.info(f"❌ Failed to update GitHub PR: {e}")
            # Fallback to console output
            logger.info("Description:")
            logger.info(payload.description)
