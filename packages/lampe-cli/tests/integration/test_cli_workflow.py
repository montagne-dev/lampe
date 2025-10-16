from unittest.mock import AsyncMock, MagicMock

import pytest

from lampe.cli.commands.describe import describe
from lampe.cli.orchestrators.pr_description import (
    AgenticGeneratorAdapter,
    DefaultGeneratorAdapter,
    PRDescriptionConfig,
    PRDescriptionOrchestratorWorkflow,
    PRDescriptionStart,
)
from lampe.cli.providers.console import ConsoleProvider


def test_full_workflow_default_variant(sample_repo_path, mock_llm_response, mocker):
    """Test the complete workflow with default variant."""
    # Mock the generator to return a specific response
    mock_generator = AsyncMock()
    mock_result = MagicMock()
    mock_result.description = "Generated description"
    mock_generator.generate.return_value = mock_result

    # Mock the provider
    mock_provider = MagicMock()

    # Mock the workflow creation
    mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow")
    mocker.patch("lampe.cli.commands.describe.Provider.create_provider", return_value=mock_provider)
    mocker.patch("lampe.cli.commands.describe.DefaultGeneratorAdapter", return_value=mock_generator)
    mocker.patch("lampe.cli.commands.describe.initialize")

    # Mock the workflow run method
    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock()
    mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow", return_value=mock_workflow)

    describe(
        repo=sample_repo_path,
        repo_full_name="owner/repo",
        base="abc123",
        head="def456",
        title="Test PR",
        variant="default",
        files_exclude=None,
        files_reinclude=None,
        output="console",
    )

    # Verify the workflow was called
    mock_workflow.run.assert_called_once()


def test_full_workflow_agentic_variant(sample_repo_path, mock_llm_response, mocker):
    """Test the complete workflow with agentic variant."""
    # Mock the generator to return a specific response
    mock_generator = AsyncMock()
    mock_result = MagicMock()
    mock_result.description = "Agentic description"
    mock_generator.generate.return_value = mock_result

    # Mock the provider
    mock_provider = MagicMock()

    # Mock the workflow creation
    mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow")
    mocker.patch("lampe.cli.commands.describe.Provider.create_provider", return_value=mock_provider)
    mocker.patch("lampe.cli.commands.describe.AgenticGeneratorAdapter", return_value=mock_generator)
    mocker.patch("lampe.cli.commands.describe.initialize")

    # Mock the workflow run method
    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock()
    mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow", return_value=mock_workflow)

    describe(
        repo=sample_repo_path,
        repo_full_name="owner/repo",
        base="abc123",
        head="def456",
        title="Test PR",
        variant="agentic",
        output="console",
        files_exclude=None,
        files_reinclude=None,
    )

    # Verify the workflow was called
    mock_workflow.run.assert_called_once()


def test_workflow_with_file_exclusions(sample_repo_path, mock_llm_response, mocker):
    """Test workflow with file exclusion patterns."""
    # Mock the generator to return a specific response
    mock_generator = AsyncMock()
    mock_result = MagicMock()
    mock_result.description = "Filtered description"
    mock_generator.generate.return_value = mock_result

    # Mock the provider
    mock_provider = MagicMock()

    # Mock the workflow creation
    mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow")
    mocker.patch("lampe.cli.commands.describe.Provider.create_provider", return_value=mock_provider)
    mocker.patch("lampe.cli.commands.describe.DefaultGeneratorAdapter", return_value=mock_generator)
    mocker.patch("lampe.cli.commands.describe.initialize")

    # Mock the workflow run method
    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock()
    mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow", return_value=mock_workflow)

    describe(
        repo=sample_repo_path,
        repo_full_name="owner/repo",
        base="abc123",
        head="def456",
        title="Test PR",
        files_exclude=["*.md", "*.txt"],
        files_reinclude=["!README.md"],
        output="console",
    )

    # Verify the workflow was called
    mock_workflow.run.assert_called_once()


def test_workflow_with_custom_parameters(sample_repo_path, mock_llm_response, mocker):
    """Test workflow with custom parameters."""
    # Mock the generator to return a specific response
    mock_generator = AsyncMock()
    mock_result = MagicMock()
    mock_result.description = "Custom description"
    mock_generator.generate.return_value = mock_result

    # Mock the provider
    mock_provider = MagicMock()

    # Mock the workflow creation
    mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow")
    mocker.patch("lampe.cli.commands.describe.Provider.create_provider", return_value=mock_provider)
    mocker.patch("lampe.cli.commands.describe.DefaultGeneratorAdapter", return_value=mock_generator)
    mocker.patch("lampe.cli.commands.describe.initialize")

    # Mock the workflow run method
    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock()
    mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow", return_value=mock_workflow)

    describe(
        repo=sample_repo_path,
        repo_full_name="owner/repo",
        base="abc123",
        head="def456",
        title="Custom PR Title",
        variant="default",
        truncation_tokens=50000,
        files_exclude=None,
        files_reinclude=None,
        timeout=30,
        verbose=True,
        output="console",
    )

    # Verify the workflow was called
    mock_workflow.run.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_workflow_integration(sample_repository, sample_pull_request, mock_llm_response):
    """Test the orchestrator workflow integration."""
    # Mock the generator
    mock_generator = MagicMock()
    mock_generator.generate = AsyncMock(return_value=MagicMock(description="Orchestrator description"))

    # Mock the provider
    mock_provider = MagicMock()

    # Create the workflow
    workflow = PRDescriptionOrchestratorWorkflow(provider=mock_provider, generator=mock_generator)

    # Create config
    config = PRDescriptionConfig(files_exclude_patterns=["*.md"], truncation_tokens=50000, verbose=True)

    # Create start event
    start_event = PRDescriptionStart(repository=sample_repository, pull_request=sample_pull_request, config=config)

    # Run the workflow
    result = await workflow.run(start_event=start_event)

    # Verify generator was called
    mock_generator.generate.assert_called_once_with(
        repository=sample_repository,
        pull_request=sample_pull_request,
        files_exclude_patterns=["*.md"],
        files_reinclude_patterns=None,
        truncation_tokens=50000,
        timeout=None,
        verbose=True,
    )

    # Verify provider was called
    mock_provider.deliver_pr_description.assert_called_once()

    # Verify result
    assert result["description"] == "Orchestrator description"


@pytest.mark.asyncio
async def test_console_provider_integration(sample_repository, sample_pull_request, mocker):
    """Test console provider integration."""
    # Test text format
    mock_print = mocker.patch("builtins.print")
    provider = ConsoleProvider(repository=sample_repository, pull_request=sample_pull_request)

    from lampe.cli.providers.base import PRDescriptionPayload

    payload = PRDescriptionPayload(description="Test description")
    provider.deliver_pr_description(payload)

    mock_print.assert_called_once_with("Test description")

    # Reset mock for next test
    mock_print.reset_mock()

    provider = ConsoleProvider(repository=sample_repository, pull_request=sample_pull_request)

    payload = PRDescriptionPayload(description="Test description")
    provider.deliver_pr_description(payload)

    mock_print.assert_called_once_with("Test description")


@pytest.mark.asyncio
async def test_generator_adapters_integration(sample_repository, sample_pull_request, mocker):
    """Test generator adapters integration."""
    # Test DefaultGeneratorAdapter
    mock_default = mocker.patch("lampe.cli.orchestrators.pr_description.generate_default_description")
    mock_result = MagicMock()
    mock_result.description = "Default description"
    mock_default.return_value = mock_result

    adapter = DefaultGeneratorAdapter()
    result = await adapter.generate(
        repository=sample_repository,
        pull_request=sample_pull_request,
        files_exclude_patterns=["*.md"],
        truncation_tokens=50000,
        verbose=True,
    )

    mock_default.assert_called_once()
    assert getattr(result, "description") == "Default description"

    # Test AgenticGeneratorAdapter
    mock_agentic = mocker.patch("lampe.cli.orchestrators.pr_description.generate_agentic_description")
    mock_result = MagicMock()
    mock_result.description = "Agentic description"
    mock_agentic.return_value = mock_result

    adapter = AgenticGeneratorAdapter()
    result = await adapter.generate(
        repository=sample_repository,
        pull_request=sample_pull_request,
        files_exclude_patterns=["*.md"],
        truncation_tokens=50000,
        verbose=True,
    )

    mock_agentic.assert_called_once()
    assert getattr(result, "description") == "Agentic description"


def test_error_handling_in_workflow(sample_repo_path, mocker):
    """Test error handling in the workflow."""
    # Mock the generator to raise an error
    mock_generator = AsyncMock()
    mock_generator.generate.side_effect = Exception("LLM error")

    # Mock the provider
    mock_provider = MagicMock()

    # Mock the workflow creation
    mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow")
    mocker.patch("lampe.cli.commands.describe.Provider.create_provider", return_value=mock_provider)
    mocker.patch("lampe.cli.commands.describe.DefaultGeneratorAdapter", return_value=mock_generator)
    mocker.patch("lampe.cli.commands.describe.initialize")

    # Mock the workflow run method to propagate the error
    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock(side_effect=Exception("LLM error"))
    mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow", return_value=mock_workflow)

    # The function should propagate the error
    with pytest.raises(Exception, match="LLM error"):
        describe(
            repo=sample_repo_path,
            repo_full_name="owner/repo",
            base="abc123",
            head="def456",
            title="Test PR",
            files_exclude=None,
            files_reinclude=None,
            output="console",
        )


def test_workflow_with_llm_mocking(sample_repo_path, mock_llm_response, mocker):
    """Test workflow with proper LLM mocking."""
    # Mock the generator to return a specific response
    mock_generator = AsyncMock()
    mock_result = MagicMock()
    mock_result.description = """### What change is being made?

Added new features.

### Why are these changes being made?

To improve functionality.
"""
    mock_generator.generate.return_value = mock_result

    # Mock the provider
    mock_provider = MagicMock()

    # Mock the workflow creation
    mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow")
    mocker.patch("lampe.cli.commands.describe.Provider.create_provider", return_value=mock_provider)
    mocker.patch("lampe.cli.commands.describe.DefaultGeneratorAdapter", return_value=mock_generator)
    mocker.patch("lampe.cli.commands.describe.initialize")

    # Mock the workflow run method
    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock()
    mocker.patch("lampe.cli.commands.describe.PRDescriptionOrchestratorWorkflow", return_value=mock_workflow)

    describe(
        repo=sample_repo_path,
        repo_full_name="owner/repo",
        base="abc123",
        head="def456",
        title="Test PR",
        variant="default",
        files_exclude=None,
        files_reinclude=None,
        output="console",
    )

    # Verify the workflow was called
    mock_workflow.run.assert_called_once()
