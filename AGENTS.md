# AGENTS.md

## Project Overview

Lampe is a code review agent system that uses specialized AI agents to perform comprehensive pull request reviews. The system follows a multi-agent architecture where different agents focus on specific aspects of code quality.

## Prompt Separation Pattern

**CRITICAL**: Always separate hardcoded prompts from workflow/agent implementation files.

### Prompt File Structure

- Create separate `*_prompt.py` files for all hardcoded prompts
- Use descriptive names: `{agent_name}_prompt.py`, `{workflow_name}_prompt.py`
- Never include hardcoded prompt strings directly in workflow/agent implementation files

### File Organization

```
workflows/
├── {workflow_name}_prompt.py          # Main workflow prompts
├── {workflow_name}.py                 # Workflow implementation
└── agents/
    ├── {agent_name}_prompt.py         # Agent-specific prompts
    ├── {agent_name}.py                # Agent implementation
    └── specialized_agent_base_prompt.py # Base agent prompts
```

### Implementation Pattern

```python
# {agent_name}_prompt.py
AGENT_SYSTEM_PROMPT = """
[Prompt content here]
"""

# {agent_name}.py
from .{agent_name}_prompt import AGENT_SYSTEM_PROMPT
from llama_index.core.workflow import Workflow

class AgentClass(Workflow):
    def __init__(self, *args, **kwargs):
        super().__init__(system_prompt=AGENT_SYSTEM_PROMPT, *args, **kwargs)
```

## Code Style

- Python strict mode with type hints
- Single quotes for strings
- Use functional patterns where possible
- Group imports: standard library, third-party, local imports
- Sort imports alphabetically within each group

## Testing Instructions

- Run tests: `pytest packages/lampe-review/tests/`
- Run linting: `ruff check packages/lampe-review/`
- Fix any test or type errors until the whole suite is green
- Add or update tests for the code you change, even if nobody asked

## PR Instructions

- Title format: `[lampe-review] <Title>`
- Always run `ruff check` and `pytest` before committing
- Ensure all prompts are in separate `*_prompt.py` files
- Verify imports are correct and organized

## Security Considerations

- Never hardcode API keys or secrets in prompts
- Use environment variables for sensitive configuration
- Validate all inputs in agent workflows

## Build Commands

- Install dependencies: `uv sync`
- Run type checking: `mypy packages/lampe-review/`
- Format code: `ruff format packages/lampe-review/`

## Agent Workflow Guidelines

- Each specialized agent should focus on one domain (security, performance, etc.)
- Use the multi-agent pipeline for comprehensive reviews
- Maintain separation between prompt content and business logic
- Follow the established pattern for prompt file organization
