# lampe-cli Test Suite

This directory contains comprehensive unit and integration tests for the lampe-cli package.

## Test Structure

```
tests/
├── conftest.py                 # Common fixtures and test configuration
├── fixtures/                   # Test data and mock objects
│   ├── cli_test_data.json     # Sample test data
│   └── test_llm_mocks.py      # LLM mocking utilities
├── unit/                       # Unit tests
│   ├── test_commands_describe.py
│   ├── test_orchestrators_pr_description.py
│   └── test_providers_console.py
├── integration/               # Integration tests
│   └── test_cli_workflow.py
├── test_runner.py             # Test runner script
└── README.md                  # This file
```

## Test Categories

### Unit Tests

- **Commands**: Test the CLI command functions (`describe.py`)
- **Orchestrators**: Test workflow orchestration logic (`pr_description.py`)
- **Providers**: Test output providers (`console.py`)

### Integration Tests

- **CLI Workflow**: Test the complete end-to-end workflow
- **LLM Integration**: Test with mocked LLM responses
- **Error Handling**: Test error scenarios and edge cases

## Key Features

### LLM Mocking

The test suite focuses heavily on mocking the LLM as requested:

- Mock LLM responses for different scenarios
- Test both default and agentic variants
- Handle markdown-wrapped responses
- Test error conditions and timeouts

### Comprehensive Coverage

- All major components are tested
- Both unit and integration test levels
- Error handling and edge cases
- Different output formats (text/JSON)

## Running Tests

### Prerequisites

Install test dependencies:

```bash
cd packages/lampe-cli
uv pip install -e ".[test]"
```

### Using the Test Runner

```bash
# Run all tests
python tests/test_runner.py

# Run only unit tests
python tests/test_runner.py --type unit

# Run only integration tests
python tests/test_runner.py --type integration

# Run with verbose output
python tests/test_runner.py --verbose

# Run with coverage reporting
python tests/test_runner.py --coverage
```

### Using pytest directly

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run with coverage
pytest --cov=lampe.cli --cov-report=html
```

## Test Fixtures

### Common Fixtures (conftest.py)

- `mock_llm_response`: Standard LLM response mock
- `mock_llm_response_with_markdown`: LLM response with markdown wrapping
- `sample_repository`: Temporary repository for testing
- `sample_pull_request`: Sample PR data
- `sample_repo_path`: Temporary directory path
- `mock_git_diff`: Sample git diff output

### LLM Mock Utilities (fixtures/test_llm_mocks.py)

- Predefined mock responses for common scenarios
- Error condition mocks
- Tool call mocks
- Workflow result mocks

## Test Data

### Sample Data (fixtures/cli_test_data.json)

- Sample PR and repository data
- Expected LLM responses
- Test configurations
- Expected output formats

## Mocking Strategy

The test suite uses a comprehensive mocking strategy:

1. **LLM Mocking**: All LLM calls are mocked to avoid external dependencies
2. **File System**: Temporary directories for repository testing
3. **Git Operations**: Mocked git diff and commit operations
4. **Console Output**: Captured and verified print statements
5. **Async Operations**: Proper async/await testing with pytest-asyncio

## Test Scenarios

### Unit Test Scenarios

- Component initialization
- Method parameter passing
- Return value validation
- Error handling
- Configuration options

### Integration Test Scenarios

- Complete workflow execution
- LLM response processing
- Output formatting (text/JSON)
- File exclusion patterns
- Custom parameters
- Error propagation

## Coverage Goals

The test suite aims for:

- **Unit Tests**: 90%+ coverage of individual components
- **Integration Tests**: Full workflow coverage
- **Error Scenarios**: Comprehensive error handling tests
- **Edge Cases**: Configuration and parameter edge cases

## Continuous Integration

The test suite is designed to run in CI environments:

- No external dependencies (all LLMs mocked)
- Fast execution (no real API calls)
- Deterministic results
- Comprehensive error reporting
