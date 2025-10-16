import logging

import git
from packaging import version

from lampe.core.loggingconfig import LAMPE_LOGGER_NAME

logger = logging.getLogger(name=LAMPE_LOGGER_NAME)

# NOTE: Git 2.49.0+ required for --revision flag support
MINIMUM_GIT_VERSION = "2.49.0"


def valid_git_version_available() -> bool:
    """
    Check if the installed Git version meets the minimum requirement.

    Returns
    -------
    :
        True if Git version meets requirement, False otherwise
    """
    try:
        version_line = git.Git().version().strip()
        if not version_line:
            logger.critical("Unable to determine Git version from output.")
            return False

        # Extract version number from output like "git version 2.39.0"
        version_parts = version_line.split()
        if len(version_parts) < 3:
            logger.critical(f"Unexpected Git version output format: {version_line}")
            return False

        current_version = version_parts[2]

        # Handle version strings with additional info (e.g., "2.39.0.windows.1")
        # Take only the semantic version part
        current_version = current_version.split(".")[0:3]
        current_version = ".".join(current_version)

        if version.parse(current_version) >= version.parse(MINIMUM_GIT_VERSION):
            logger.debug(f"Git version {current_version} meets requirement ({MINIMUM_GIT_VERSION}+)")
            return True
        else:
            logger.critical(
                f"CRITICAL: Git version {current_version} does not meet the minimum requirement "
                f"({MINIMUM_GIT_VERSION}+). The lampe-sdk requires Git {MINIMUM_GIT_VERSION} or higher "
                f"for proper functionality. Git operations may fail or behave unexpectedly. "
                f"Please upgrade your Git installation. See the README for installation instructions."
            )
            return False
    except Exception as e:
        logger.critical(f"Unexpected error while checking Git version: {e}")
        return False


def init_git():
    """Initialize Git configuration and check version requirements."""
    logger.debug("Initializing Git configuration...")
    valid_git_version_available()
