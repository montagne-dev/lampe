# AGENTS.md

## Project Overview

Lampe is a code review agent system that uses an agentic orchestrator to perform comprehensive pull request reviews (intent extraction, skill selection, validation agents, and aggregation).

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
- Validation agents in the agentic workflow focus on specific verification tasks.
- Maintain separation between prompt content and business logic.
- Follow the established pattern for prompt file organization.

## Model Configuration

LLM models can be overridden via environment variables. Use `get_model(env_var, default)` from `lampe.core.llmconfig`. Env vars: `LAMPE_MODEL_DESCRIBE`, `LAMPE_MODEL_QUICK_REVIEW`, `LAMPE_MODEL_QUICK_REVIEW_HALLUCINATION_FILTER`, `LAMPE_MODEL_REVIEW_AGGREGATION`, `LAMPE_MODEL_REVIEW_INTENT`, `LAMPE_MODEL_REVIEW_VALIDATION`. The health check validates that configured models have the corresponding API key.

## Review Variants

The CLI supports `--variant` for the review command (default: `agentic`). Currently only the agentic variant is available; additional variants may be added in the future.

## Agentic Review Workflow

The agentic review workflow (default) uses an orchestrator that:

1. **Extracts PR intent** from title, description, and diff
2. **Discovers skills** — any `SKILL.md` file in the repo (e.g. `.cursor/skills/`, `docs/`, `guidelines/`)
3. **Selects applicable skills** (only when skills exist) based on PR intent
4. **Plans validation tasks** — orchestrator formulates concrete validation questions for basic agents; skills define tasks for skill-augmented agents
5. **Spawns validation agents** (basic or skill-augmented) to verify each task
6. **Aggregates and QA** — deduplicates, prioritizes, selects top feedback

### Skills for Agentic Review

Repositories can add **skills** that guide validation. Place `SKILL.md` files anywhere in the repo:

- `.cursor/skills/<skill-name>/SKILL.md`
- `.lampe/skills/<skill-name>/SKILL.md`
- `docs/guidelines/SKILL.md` (or any other path)

**SKILL.md format** (Cursor-style):

```markdown
---
name: django-data-management
description: Guidelines for Django models, migrations, and data handling. Use when reviewing changes to models.py, migrations, or data-related code.
---

# Django Data Management

## Review Checklist

- Migrations are reversible when possible
- No raw SQL without proper escaping
- Use select_related/prefetch_related for N+1 avoidance
```

The Skill Selector Agent picks which skills apply to each PR. Skill-augmented validation agents receive the skill content in their prompt.
