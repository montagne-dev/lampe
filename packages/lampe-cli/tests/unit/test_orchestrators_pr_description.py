from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lampe.cli.orchestrators.pr_description import (
    AgenticGeneratorAdapter,
    DefaultGeneratorAdapter,
    PRDescriptionConfig,
    PRDescriptionOrchestratorWorkflow,
    PRDescriptionStart,
)


def test_pr_description_config_default():
    """Test default configuration values."""
    config = PRDescriptionConfig()
    assert config.files_exclude_patterns is None
    assert config.files_reinclude_patterns is None
    assert config.truncation_tokens == 100_000
    assert config.timeout is None
    assert config.verbose is False


def test_pr_description_config_custom():
    """Test custom configuration values."""
    config = PRDescriptionConfig(
        files_exclude_patterns=["*.md"],
        files_reinclude_patterns=["!README.md"],
        truncation_tokens=50000,
        timeout=30,
        verbose=True,
    )
    assert config.files_exclude_patterns == ["*.md"]
    assert config.files_reinclude_patterns == ["!README.md"]
    assert config.truncation_tokens == 50000
    assert config.timeout == 30
    assert config.verbose is True


@pytest.mark.asyncio
async def test_default_generator_adapter_generate(sample_repository, sample_pull_request, mock_llm_response):
    """Test that DefaultGeneratorAdapter calls the default workflow."""
    with patch("lampe.cli.orchestrators.pr_description.generate_default_description") as mock_generate:
        mock_generate.return_value = MagicMock(description="Test description")

        adapter = DefaultGeneratorAdapter()
        await adapter.generate(
            repository=sample_repository,
            pull_request=sample_pull_request,
            files_exclude_patterns=["*.md"],
            files_reinclude_patterns=["!README.md"],
            truncation_tokens=50000,
            timeout=30,
            verbose=True,
            metadata={"test": "data"},
        )

        # Verify the call
        mock_generate.assert_called_once_with(
            repository=sample_repository,
            pull_request=sample_pull_request,
            files_exclude_patterns=["*.md"],
            files_reinclude_patterns=["!README.md"],
            truncation_tokens=50000,
            timeout=30,
            verbose=True,
            metadata={"test": "data"},
        )


@pytest.mark.asyncio
async def test_default_generator_adapter_generate_with_defaults(sample_repository, sample_pull_request):
    """Test generate with default parameters."""
    with patch("lampe.cli.orchestrators.pr_description.generate_default_description") as mock_generate:
        mock_generate.return_value = MagicMock(description="Test description")

        adapter = DefaultGeneratorAdapter()
        await adapter.generate(repository=sample_repository, pull_request=sample_pull_request)

        # Verify default parameters
        mock_generate.assert_called_once_with(
            repository=sample_repository,
            pull_request=sample_pull_request,
            files_exclude_patterns=None,
            files_reinclude_patterns=None,
            truncation_tokens=100_000,
            timeout=None,
            verbose=False,
            metadata=None,
        )


@pytest.mark.asyncio
async def test_agentic_generator_adapter_generate(sample_repository, sample_pull_request):
    """Test that AgenticGeneratorAdapter calls the agentic workflow."""
    with patch("lampe.cli.orchestrators.pr_description.generate_agentic_description") as mock_generate:
        mock_generate.return_value = MagicMock(description="Agentic description")

        adapter = AgenticGeneratorAdapter()
        await adapter.generate(
            repository=sample_repository,
            pull_request=sample_pull_request,
            files_exclude_patterns=["*.md"],
            files_reinclude_patterns=["!README.md"],
            truncation_tokens=50000,
            timeout=30,
            verbose=True,
            metadata={"test": "data"},
        )

        # Verify the call (agentic ignores some parameters)
        mock_generate.assert_called_once_with(
            repository=sample_repository,
            pull_request=sample_pull_request,
            files_exclude_patterns=["*.md"],
            timeout=30,
            verbose=True,
        )


@pytest.mark.asyncio
async def test_agentic_generator_adapter_ignores_unsupported_params(sample_repository, sample_pull_request):
    """Test that AgenticGeneratorAdapter ignores unsupported parameters."""
    with patch("lampe.cli.orchestrators.pr_description.generate_agentic_description") as mock_generate:
        mock_generate.return_value = MagicMock(description="Agentic description")

        adapter = AgenticGeneratorAdapter()
        await adapter.generate(
            repository=sample_repository,
            pull_request=sample_pull_request,
            files_reinclude_patterns=["!README.md"],  # Should be ignored
            truncation_tokens=50000,  # Should be ignored
            metadata={"test": "data"},  # Should be ignored
        )

        # Verify only supported parameters are passed
        mock_generate.assert_called_once_with(
            repository=sample_repository,
            pull_request=sample_pull_request,
            files_exclude_patterns=None,
            timeout=None,
            verbose=False,
        )


def test_orchestrator_workflow_init(sample_repository, sample_pull_request):
    """Test workflow initialization."""
    mock_provider = MagicMock()
    mock_generator = MagicMock()

    workflow = PRDescriptionOrchestratorWorkflow(
        provider=mock_provider, generator=mock_generator, timeout=30, verbose=True
    )

    assert workflow.provider == mock_provider
    assert workflow.generator == mock_generator


@pytest.mark.asyncio
async def test_orchestrator_workflow_run_generation_step(sample_repository, sample_pull_request):
    """Test the run_generation step."""
    mock_provider = MagicMock()
    mock_generator = MagicMock()
    mock_generator.generate = AsyncMock(return_value=MagicMock(description="Test description"))

    workflow = PRDescriptionOrchestratorWorkflow(provider=mock_provider, generator=mock_generator)

    config = PRDescriptionConfig(files_exclude_patterns=["*.md"], truncation_tokens=50000, verbose=True)

    start_event = PRDescriptionStart(repository=sample_repository, pull_request=sample_pull_request, config=config)

    result = await workflow.run_generation(start_event)

    # Verify generator was called with correct parameters
    mock_generator.generate.assert_called_once_with(
        repository=sample_repository,
        pull_request=sample_pull_request,
        files_exclude_patterns=["*.md"],
        files_reinclude_patterns=None,
        truncation_tokens=50000,
        timeout=None,
        verbose=True,
    )

    # Verify result structure
    assert result.result["description"] == "Test description"


@pytest.mark.asyncio
async def test_orchestrator_workflow_deliver_step(sample_repository, sample_pull_request):
    """Test the deliver step."""
    mock_provider = MagicMock()
    mock_generator = MagicMock()

    workflow = PRDescriptionOrchestratorWorkflow(provider=mock_provider, generator=mock_generator)

    # Create a mock event with result
    from llama_index.core.workflow import Event

    event = Event(result={"description": "Test description"})

    result = await workflow.deliver(event)

    # Verify provider was called
    mock_provider.deliver_pr_description.assert_called_once()
    call_args = mock_provider.deliver_pr_description.call_args[0][0]
    assert call_args.description == "Test description"

    # Verify result
    assert result.result["description"] == "Test description"


@pytest.mark.asyncio
async def test_orchestrator_workflow_full_run(sample_repository, sample_pull_request):
    """Test the full workflow execution."""
    mock_provider = MagicMock()
    mock_generator = MagicMock()
    mock_generator.generate = AsyncMock(return_value=MagicMock(description="Test description"))

    workflow = PRDescriptionOrchestratorWorkflow(provider=mock_provider, generator=mock_generator)

    config = PRDescriptionConfig(verbose=True)
    start_event = PRDescriptionStart(repository=sample_repository, pull_request=sample_pull_request, config=config)

    # Run the full workflow
    result = await workflow.run(start_event=start_event)

    # Verify generator was called
    mock_generator.generate.assert_called_once()

    # Verify provider was called
    mock_provider.deliver_pr_description.assert_called_once()

    # Verify final result
    assert result["description"] == "Test description"


def test_pr_description_start_event_creation(sample_repository, sample_pull_request):
    """Test PRDescriptionStart event creation."""
    config = PRDescriptionConfig(verbose=True)

    start_event = PRDescriptionStart(repository=sample_repository, pull_request=sample_pull_request, config=config)

    assert start_event.repository == sample_repository
    assert start_event.pull_request == sample_pull_request
    assert start_event.config == config
