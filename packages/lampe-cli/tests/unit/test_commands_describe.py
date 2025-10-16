from lampe.cli.commands.describe import describe


def test_run_describe_agentic_variant(sample_repo_path, mocker):
    """Test run_describe with agentic variant."""
    mocker.patch("lampe.cli.commands.describe.initialize")
    mock_workflow = mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow")

    mock_workflow_instance = mocker.MagicMock()
    mock_workflow.return_value = mock_workflow_instance

    # Mock the async run method
    async def mock_run(start_event):
        return mocker.MagicMock()

    mock_workflow_instance.run = mock_run

    # Test the function
    describe(
        repo=sample_repo_path,
        repo_full_name="owner/repo",
        base="abc123",
        head="def456",
        title="Test PR",
        variant="agentic",
        files_exclude=None,
        files_reinclude=None,
        output="console",
    )

    # Verify workflow was created
    mock_workflow.assert_called_once()


def test_run_describe_with_exclude_patterns(sample_repo_path, mocker):
    """Test run_describe with file exclusion patterns."""
    mocker.patch("lampe.cli.commands.describe.initialize")
    mock_workflow = mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow")

    mock_workflow_instance = mocker.MagicMock()
    mock_workflow.return_value = mock_workflow_instance

    # Mock the async run method
    async def mock_run(start_event):
        return mocker.MagicMock()

    mock_workflow_instance.run = mock_run

    # Test the function with exclude patterns
    describe(
        repo=sample_repo_path,
        repo_full_name="owner/repo",
        base="abc123",
        head="def456",
        title="Test PR",
        files_exclude=["*.md", "*.txt"],
        files_reinclude=["!README.md"],
        truncation_tokens=50000,
        timeout=30,
        verbose=True,
        output="console",
    )

    # Verify workflow was created
    mock_workflow.assert_called_once()


def test_run_describe_initializes_core(sample_repo_path, mocker):
    """Test that run_describe calls initialize."""
    mock_init = mocker.patch("lampe.cli.commands.describe.initialize")
    mock_workflow = mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow")

    mock_workflow_instance = mocker.MagicMock()
    mock_workflow.return_value = mock_workflow_instance

    # Mock the async run method
    async def mock_run(start_event):
        return mocker.MagicMock()

    mock_workflow_instance.run = mock_run

    describe(
        repo=sample_repo_path,
        repo_full_name="owner/repo",
        base="abc123",
        head="def456",
        output="console",
        title="Test PR",
        files_exclude=None,
        files_reinclude=None,
    )

    # Verify initialize was called
    mock_init.assert_called_once()


def test_run_describe_creates_correct_models(sample_repo_path, mocker):
    """Test that run_describe creates correct Repository and PullRequest models."""
    mocker.patch("lampe.cli.commands.describe.initialize")
    mock_workflow = mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow")

    mock_workflow_instance = mocker.MagicMock()
    mock_workflow.return_value = mock_workflow_instance

    # Mock the async run method
    async def mock_run(start_event):
        # Verify the start event has correct models
        assert start_event.repository.local_path == str(sample_repo_path)
        assert start_event.pull_request.title == "Custom Title"
        assert start_event.pull_request.base_commit_hash == "base123"
        assert start_event.pull_request.head_commit_hash == "head456"
        return mocker.MagicMock()

    mock_workflow_instance.run = mock_run

    describe(
        repo=sample_repo_path,
        repo_full_name="owner/repo",
        base="base123",
        head="head456",
        title="Custom Title",
        files_exclude=None,
        files_reinclude=None,
        output="console",
    )

    # Verify workflow was called
    mock_workflow.assert_called_once()
