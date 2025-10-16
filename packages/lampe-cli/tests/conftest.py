import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lampe.core.data_models import PullRequest, Repository


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    mock = MagicMock()
    mock.message.content = """### What change is being made?

Added a new feature.

### Why are these changes being made?

To improve the product.
"""
    return mock


@pytest.fixture
def mock_llm_response_with_markdown():
    """Mock LLM response with markdown code blocks for testing."""
    mock = MagicMock()
    mock.message.content = """
```md
### What change is being made?

Added a new feature.
```
"""
    return mock


@pytest.fixture
def sample_repository():
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Repository(local_path=temp_dir)


@pytest.fixture
def sample_pull_request():
    """Create a sample pull request for testing."""
    return PullRequest(
        number=1,
        title="Add new feature",
        body="This PR adds a new feature.",
        base_commit_hash="abc123",
        base_branch_name="main",
        head_commit_hash="def456",
        head_branch_name="feature/new-feature",
    )


@pytest.fixture
def sample_repo_path():
    """Create a temporary directory for repository testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_git_diff():
    """Mock git diff output."""
    return """diff --git a/src/feature.py b/src/feature.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/src/feature.py
@@ -0,0 +1,5 @@
+def new_feature():
+    \"\"\"New feature implementation.\"\"\"
+    return "Hello, World!"
+
+def helper_function():
+    return True
"""
