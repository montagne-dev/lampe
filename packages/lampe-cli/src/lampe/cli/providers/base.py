from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

from lampe.core.data_models import PullRequest, Repository
from lampe.review.workflows.pr_review.data_models import AgentReviewOutput


@dataclass
class PRDescriptionPayload:
    description: str

    @property
    def description_with_title(self) -> str:
        return f"## 🔦 description\n{self.description}"


@dataclass
class PRReviewPayload:
    reviews: list[AgentReviewOutput]  # List of agent review outputs

    @property
    def review_markdown(self) -> str:
        review_text = "## 🔍 Code Review\n\n"
        for agent_review in self.reviews:
            review_text += f"### {agent_review.agent_name}\n\n"
            review_text += f"**Focus Areas:** {', '.join(agent_review.focus_areas)}\n\n"

            if agent_review.summary:
                review_text += f"**Agent Summary:** {agent_review.summary}\n\n"

            for file_review in agent_review.reviews:
                review_text += f"#### {file_review.file_path}\n"
                review_text += f"**Summary:** {file_review.summary}\n\n"

                if file_review.line_comments:
                    review_text += "**Line Comments:**\n"
                    for line, comment in file_review.line_comments.items():
                        review_text += f"- Line {line}: {comment}\n"
                    review_text += "\n"

                if file_review.structured_comments:
                    review_text += "**Structured Comments:**\n"
                    for comment in file_review.structured_comments:
                        review_text += f"- Line {comment.line_number} ({comment.severity}): {comment.comment}\n"
                    review_text += "\n"

            if agent_review.sources:
                review_text += "**Sources:**\n"
                for source in agent_review.sources:
                    review_text += f"- **{source.tool_name}**: {source.tool_output.content}\n"
                review_text += "\n"

            review_text += "---\n\n"
        return review_text


class ProviderType(StrEnum):
    """Available provider types."""

    CONSOLE = "console"
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    AUTO = "auto"


class Provider(ABC):
    """Abstract provider for delivering workflow outputs."""

    def __init__(self, repository: Repository, pull_request: PullRequest) -> None:
        self.repository = repository
        self.pull_request = pull_request

    @abstractmethod
    def deliver_pr_description(self, payload: PRDescriptionPayload) -> None:
        """Deliver a PR description to the configured destination."""
        ...

    @abstractmethod
    def deliver_pr_review(self, payload: PRReviewPayload) -> None:
        """Deliver a PR review to the configured destination."""
        ...

    @abstractmethod
    def healthcheck(self) -> None:
        """Check if the provider is healthy and can connect to the service."""
        ...

    @staticmethod
    def detect_provider_type() -> ProviderType:
        """Detect the appropriate provider type based on available environment variables."""
        # Priority order for provider detection
        env_var_mapping = {
            "GITHUB_API_TOKEN": ProviderType.GITHUB,
            "GITHUB_TOKEN": ProviderType.GITHUB,
            "LAMPE_GITHUB_TOKEN": ProviderType.GITHUB,
            "LAMPE_GITHUB_APP_ID": ProviderType.GITHUB,
            "LAMPE_GITHUB_APP_PRIVATE_KEY": ProviderType.GITHUB,
            "GITLAB_API_TOKEN": ProviderType.GITLAB,
            "LAMPE_BITBUCKET_TOKEN": ProviderType.BITBUCKET,
            "LAMPE_BITBUCKET_APP_KEY": ProviderType.BITBUCKET,
            "BITBUCKET_WORKSPACE": ProviderType.BITBUCKET,
        }

        for env_var, provider_type in env_var_mapping.items():
            if os.getenv(env_var):
                return provider_type

        # Fallback to console if no API tokens are found
        return ProviderType.CONSOLE

    @staticmethod
    def create_provider(
        provider_name: ProviderType | str, repository: Repository, pull_request: PullRequest
    ) -> "Provider":
        """Create a provider instance based on the specified type."""
        if isinstance(provider_name, str):
            # Handle "auto" detection
            if provider_name == "auto":
                provider_name = Provider.detect_provider_type()
            else:
                provider_name = ProviderType(provider_name)

        if provider_name == ProviderType.CONSOLE:
            from lampe.cli.providers.console import ConsoleProvider

            return ConsoleProvider(repository=repository, pull_request=pull_request)
        elif provider_name == ProviderType.GITHUB:
            from lampe.cli.providers.github import GitHubProvider

            return GitHubProvider(repository=repository, pull_request=pull_request)
        elif provider_name == ProviderType.BITBUCKET:
            from lampe.cli.providers.bitbucket import BitbucketProvider

            return BitbucketProvider(repository=repository, pull_request=pull_request)
        else:
            raise ValueError(f"Provider type {provider_name} not yet implemented")


def update_or_add_text_between_tags(text: str, new_text: str, feature: str) -> str:
    """
    Update the text between the tags [](lampe-sdk-{feature}-start) and [](lampe-sdk-{feature}-end)
    with new_text. If the tags don't exist, add them at the bottom of the text.
    The tags and new_text are preserved in the output.
    """
    identifier = f"lampe-sdk-{feature}-start"
    start_tag = rf"\[\]\(lampe-sdk-{feature}-start\)"
    end_tag = rf"\[\]\(lampe-sdk-{feature}-end\)"

    pattern = re.compile(rf"({start_tag})(.*?|\s*?){end_tag}", re.DOTALL)

    def replacer(match):
        return f"{match.group(1)}\n{new_text}\n[]({identifier.replace('-start', '')}-end)"

    # Try to replace the first occurrence
    result, count = pattern.subn(replacer, text, count=1)

    # If no tags were found, add them at the bottom
    if count == 0:
        result = f"{text}\n\n[]({identifier})\n{new_text}\n[]({identifier.replace('-start', '')}-end)"

    return result
