from __future__ import annotations

import logging
import os

import requests

from lampe.cli.providers.base import PRDescriptionPayload, Provider, update_or_add_text_between_tags
from lampe.core.data_models.pull_request import PullRequest
from lampe.core.data_models.repository import Repository
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)


class BitbucketProvider(Provider):
    """Bitbucket provider for delivering PR descriptions to Bitbucket Cloud API."""

    def __init__(self, repository: Repository, pull_request: PullRequest) -> None:
        if pull_request.number == 0:
            # Try Bitbucket Pipelines environment variable first, then fallback to PR_NUMBER
            pr_number = os.getenv("BITBUCKET_PR_ID") or os.getenv("PR_NUMBER")
            if not pr_number:
                raise ValueError("BITBUCKET_PR_ID or PR_NUMBER environment variable is required for Bitbucket provider")
            pull_request.number = int(pr_number)

        super().__init__(repository, pull_request)

        # Extract workspace and repository from environment variables
        self.workspace = os.getenv("BITBUCKET_WORKSPACE")
        self.repo_slug = os.getenv("BITBUCKET_REPO_SLUG")

        if not self.workspace or not self.repo_slug:
            raise ValueError(
                "BITBUCKET_WORKSPACE and BITBUCKET_REPO_SLUG environment variables are required for Bitbucket provider"
            )

        # Initialize Bitbucket client with appropriate authentication
        self.base_url, self.auth_headers = self._initialize_bitbucket_client()

    def _initialize_bitbucket_client(self) -> tuple[str, dict]:
        """Initialize Bitbucket client with appropriate authentication method."""
        # Try token authentication first (recommended)
        token = os.getenv("LAMPE_BITBUCKET_TOKEN")
        if token:
            return self._create_token_auth(token)

        # Fallback to Bitbucket App authentication
        app_key = os.getenv("LAMPE_BITBUCKET_APP_KEY")
        app_secret = os.getenv("LAMPE_BITBUCKET_APP_SECRET")
        if app_key and app_secret:
            return self._create_app_auth(app_key, app_secret)

        raise ValueError(
            "Either Bitbucket token (LAMPE_BITBUCKET_TOKEN) or app credentials "
            "(LAMPE_BITBUCKET_APP_KEY, LAMPE_BITBUCKET_APP_SECRET) environment variables "
            "are required for Bitbucket provider"
        )

    def _create_token_auth(self, token: str) -> tuple[str, dict]:
        """Create Bitbucket client using repository/workspace access token."""
        try:
            base_url = "https://api.bitbucket.org"
            auth_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            return base_url, auth_headers
        except Exception as e:
            raise ValueError(f"Failed to authenticate with Bitbucket token: {e}")

    def _create_app_auth(self, app_key: str, app_secret: str) -> tuple[str, dict]:
        """Create Bitbucket client using Bitbucket App authentication."""
        try:
            base_url = "https://api.bitbucket.org"

            # Get access token using OAuth 2.0 client credentials flow
            token_url = f"{base_url}/site/oauth2/access_token"
            token_data = {
                "grant_type": "client_credentials",
                "client_id": app_key,
                "client_secret": app_secret,
            }

            token_response = requests.post(token_url, data=token_data)
            token_response.raise_for_status()
            token_info = token_response.json()
            access_token = token_info["access_token"]

            auth_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            return base_url, auth_headers
        except Exception as e:
            raise ValueError(f"Failed to authenticate with Bitbucket App: {e}")

    def healthcheck(self) -> None:
        """Check if the Bitbucket provider is healthy and can connect to Bitbucket."""
        logger.info("🔍 Checking Bitbucket provider health...")

        # Check Bitbucket environment variables
        workspace = os.getenv("BITBUCKET_WORKSPACE")
        repo_slug = os.getenv("BITBUCKET_REPO_SLUG")

        if not workspace or not repo_slug:
            logger.info("❌ Bitbucket environment variables not set")
            logger.info("   Set both:")
            logger.info("   - BITBUCKET_WORKSPACE (e.g., 'my-workspace')")
            logger.info("   - BITBUCKET_REPO_SLUG (e.g., 'my-repo')")
            raise ValueError("BITBUCKET_WORKSPACE and BITBUCKET_REPO_SLUG environment variables are required")

        logger.info(f"✅ BITBUCKET_WORKSPACE set to: {workspace}")
        logger.info(f"✅ BITBUCKET_REPO_SLUG set to: {repo_slug}")

        # Check authentication environment variables
        token = os.getenv("LAMPE_BITBUCKET_TOKEN")
        app_key = os.getenv("LAMPE_BITBUCKET_APP_KEY")
        app_secret = os.getenv("LAMPE_BITBUCKET_APP_SECRET")

        auth_method = None
        if token:
            auth_method = "Token"
            logger.info("✅ Bitbucket token authentication detected")
        elif app_key and app_secret:
            auth_method = "App"
            logger.info("✅ Bitbucket App authentication detected")
        else:
            logger.info("❌ No Bitbucket authentication found")
            logger.info("   Set either:")
            logger.info("   - LAMPE_BITBUCKET_TOKEN for token authentication")
            logger.info("   - LAMPE_BITBUCKET_APP_KEY and LAMPE_BITBUCKET_APP_SECRET for app authentication")
            raise ValueError("No Bitbucket authentication found")

        # Test Bitbucket connection
        try:
            # Test API access by getting repository info
            repo_url = f"{self.base_url}/2.0/repositories/{workspace}/{repo_slug}"
            response = requests.get(repo_url, headers=self.auth_headers)
            response.raise_for_status()
            repo_data = response.json()

            logger.info(f"✅ Repository access confirmed: {repo_data.get('full_name', f'{workspace}/{repo_slug}')}")
            logger.info(f"   Description: {repo_data.get('description') or 'No description'}")
            logger.info(f"   Private: {repo_data.get('is_private', 'Unknown')}")
            logger.info(f"✅ Bitbucket {auth_method} authentication successful")

        except requests.exceptions.RequestException as e:
            logger.info(f"❌ Bitbucket connection failed: {e}")
            logger.info("\nTroubleshooting tips:")
            if auth_method == "Token":
                logger.info("- Verify LAMPE_BITBUCKET_TOKEN is valid and has appropriate permissions")
                logger.info("- Ensure the token has 'repositories:read' scope")
            else:
                logger.info("- Verify LAMPE_BITBUCKET_APP_KEY and LAMPE_BITBUCKET_APP_SECRET are correct")
                logger.info("- Ensure the Bitbucket App is installed on the workspace")
            raise
        except Exception as e:
            logger.info(f"❌ Unexpected error during Bitbucket healthcheck: {e}")
            raise

    def deliver_pr_description(self, payload: PRDescriptionPayload) -> None:
        """Update the PR description on Bitbucket."""
        if self.pull_request.number == 0:
            raise ValueError("Cannot update Bitbucket PR description for local run")

        try:
            # Get current PR details
            pr_url = (
                f"{self.base_url}/2.0/repositories/{self.workspace}/"
                f"{self.repo_slug}/pullrequests/{self.pull_request.number}"
            )

            # Fetch current PR to get existing description
            response = requests.get(pr_url, headers=self.auth_headers)
            response.raise_for_status()
            pr_data = response.json()

            # Update description with new content
            current_description = pr_data.get("description", "") or ""
            new_description = update_or_add_text_between_tags(
                current_description, payload.description_with_title, "description"
            )

            # Update the PR
            update_data = {"description": new_description}
            update_response = requests.put(pr_url, json=update_data, headers=self.auth_headers)
            update_response.raise_for_status()

            logger.info(f"✅ Successfully updated PR #{self.pull_request.number} description on Bitbucket")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to update Bitbucket PR: {e}")
            # Fallback to console output
            logger.info("Description:")
            logger.info(payload.description)
        except Exception as e:
            logger.error(f"❌ Unexpected error updating Bitbucket PR: {e}")
            # Fallback to console output
            logger.info("Description:")
            logger.info(payload.description)
