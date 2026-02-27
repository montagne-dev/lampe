from __future__ import annotations

import logging
import os
from urllib.parse import quote

from github import Auth, Github, GithubIntegration

from lampe.cli.providers.base import PRDescriptionPayload, Provider, PRReviewPayload, update_or_add_text_between_tags
from lampe.core.data_models.pull_request import PullRequest
from lampe.core.data_models.repository import Repository
from lampe.core.loggingconfig import LAMPE_LOGGER_NAME

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)

# Severity colors for shields.io badges
_SEVERITY_COLORS: dict[str, str] = {
    "critical": "e74c3c",
    "high": "f39c12",
    "medium": "f1c40f",
    "low": "2ecc71",
}
_CATEGORY_COLOR = "3498db"


def _badge_shield(label: str, message: str, color: str) -> str:
    """Build a shields.io-style badge markdown image."""
    encoded_label = quote(label, safe="")
    encoded_message = quote(message, safe="")
    url = f"https://img.shields.io/badge/{encoded_label}-{encoded_message}-{color}"
    return f"![{label}]({url})"


def _format_structured_comment_badges(severity: str, category: str) -> str:
    """Build severity and category badges for a structured comment."""
    sev = severity.lower()
    color = _SEVERITY_COLORS.get(sev, _CATEGORY_COLOR)
    severity_badge = _badge_shield("severity", severity, color)
    category_badge = _badge_shield("category", category, _CATEGORY_COLOR)
    return f"{severity_badge} {category_badge}"


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

    def deliver_pr_review(self, payload: PRReviewPayload) -> None:
        """Post PR review comments on GitHub."""
        if self.pull_request.number == 0:
            raise ValueError("Cannot post GitHub PR review for local run")

        try:
            repo = self.github_client.get_repo(f"{self.owner}/{self.repo_name}")
            pull_request = repo.get_pull(self.pull_request.number)

            # Post review comments for each agent review
            for agent_review in payload.reviews:
                # Post agent summary comment
                if agent_review.summary:
                    try:
                        pull_request.create_issue_comment(
                            f"## {agent_review.agent_name}\n\n"
                            f"**Focus Areas:** {', '.join(agent_review.focus_areas)}\n\n"
                            f"{agent_review.summary}"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to post agent summary for {agent_review.agent_name}: {e}")

                # Post file-specific comments
                for file_review in agent_review.reviews:
                    if file_review.line_comments:
                        # Create review comments for specific lines
                        for line, comment in file_review.line_comments.items():
                            try:
                                # Post a review comment
                                pull_request.create_review_comment(
                                    body=f"## 🔦🐛\n{comment}",
                                    commit=pull_request.head.sha,
                                    path=file_review.file_path,
                                    line=int(line),
                                )
                            except Exception as e:
                                logger.warning(f"Failed to post comment for {file_review.file_path}:{line}: {e}")
                                # Fallback: post as general comment
                                pull_request.create_issue_comment(
                                    f"**{file_review.file_path} (Line {line}):** {comment}"
                                )

                    # Post structured comments (e.g. from agentic review) as inline comments
                    if file_review.structured_comments:
                        for sc in file_review.structured_comments:
                            if getattr(sc, "muted", False):
                                continue
                            badges = _format_structured_comment_badges(sc.severity, sc.category)
                            comment_body = f"## 🔦🐛\n\n{badges}\n\n{sc.comment}"
                            try:
                                pull_request.create_review_comment(
                                    body=comment_body,
                                    commit=pull_request.head.sha,
                                    path=file_review.file_path,
                                    line=sc.line_number,
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to post comment for {file_review.file_path}:{sc.line_number}: {e}"
                                )
                                pull_request.create_issue_comment(
                                    f"**{file_review.file_path} (Line {sc.line_number}):**\n\n" f"{comment_body}"
                                )

                    # Post summary comment if no inline comments were posted
                    has_inline = bool(file_review.line_comments) or any(
                        not getattr(sc, "muted", False) for sc in file_review.structured_comments
                    )
                    if not has_inline and file_review.summary:
                        pull_request.create_issue_comment(f"**{file_review.file_path}:** {file_review.summary}")

            logger.info(f"✅ Successfully posted PR #{self.pull_request.number} review comments on GitHub")
        except Exception as e:
            logger.info(f"❌ Failed to post GitHub PR review: {e}")
            # Fallback to console output
            logger.info("Review:")
            logger.info(payload.review_markdown)

    def has_reviewed(self) -> bool:
        """Check if the token user has already reviewed this PR."""
        if self.pull_request.number == 0:
            return False

        try:
            repo = self.github_client.get_repo(f"{self.owner}/{self.repo_name}")
            pull_request = repo.get_pull(self.pull_request.number)

            # Get the authenticated user
            authenticated_user = self.github_client.get_user()

            # Check issue comments (where reviews are posted)
            comments = pull_request.get_issue_comments()
            for comment in comments:
                if comment.user.login == authenticated_user.login:
                    return True

            # Also check review comments (inline comments)
            review_comments = pull_request.get_review_comments()
            for comment in review_comments:
                if comment.user.login == authenticated_user.login:
                    return True

            return False
        except Exception as e:
            logger.warning(f"Failed to check if PR has been reviewed: {e}")
            return False
