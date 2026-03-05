# Proposed GitHub issues for Lampe

This folder contains **markdown drafts for GitHub issues** that maintainers can copy-paste into the [GitHub issue tracker](https://github.com/montagne-dev/lampe/issues) to grow the backlog and attract contributors.

## How to use

1. Open the `.md` file you want.
2. Copy the full content (title + labels + body).
3. In GitHub: **New issue** → paste the body; set the **title** from the first `#` line; add the **labels** listed at the top of the issue.

You can create all issues at once or open them gradually. Labels can be created in the repo if they don’t exist yet.

## Suggested labels (create in GitHub)

| Label            | Color  | Description                          |
|------------------|--------|--------------------------------------|
| `good first issue` | `#7057ff` | Good for new contributors           |
| `help wanted`    | `#008672` | Extra help welcome                  |
| `bug`            | `#d73a4a` | Something isn’t working             |
| `documentation`  | `#0075ca` | Docs or comments                    |
| `enhancement`    | `#a2eeef` | New feature or request              |
| `improvement`    | `#fbca04` | Improvement that isn’t a new feature |
| `testing`        | `#1d76db` | Tests or coverage                   |
| `ci`             | `#ededed` | CI/CD and automation                |
| `lampe-review`   | (any)  | Affects lampe-review package        |
| `lampe-cli`      | (any)  | Affects lampe-cli package           |
| `roadmap`        | (any)  | Planned or tracked on roadmap       |

## Index of issues

| #   | File | Summary | Suggested labels |
|-----|------|---------|------------------|
| 001 | [001-fix-readme-typo-bowser.md](001-fix-readme-typo-bowser.md) | Fix "bowser" → "browser" in README | `good first issue`, `documentation`, `bug` |
| 002 | [002-fix-pyproject-description-typo.md](002-fix-pyproject-description-typo.md) | Fix "higlight" in pyproject.toml | `good first issue`, `bug` |
| 003 | [003-contributing-add-workspace-package-instructions.md](003-contributing-add-workspace-package-instructions.md) | CONTRIBUTING: how to add a new workspace package | `good first issue`, `documentation`, `help wanted` |
| 004 | [004-specialized-agent-llm-summary.md](004-specialized-agent-llm-summary.md) | LLM-generated summary for specialized agent output | `enhancement`, `lampe-review`, `good first issue` |
| 005 | [005-aggregator-keep-metadata-sources.md](005-aggregator-keep-metadata-sources.md) | Keep agent metadata on aggregated issues | `enhancement`, `lampe-review` |
| 006 | [006-docs-agentic-review-and-skills.md](006-docs-agentic-review-and-skills.md) | Add Agentic Review / Skills to MkDocs nav | `documentation`, `good first issue` |
| 007 | [007-docs-git-version-requirement-readme.md](007-docs-git-version-requirement-readme.md) | Mention Git 2.49+ in README | `documentation`, `good first issue` |
| 008 | [008-contributing-good-first-issue-guide.md](008-contributing-good-first-issue-guide.md) | "Good first issue" guide in CONTRIBUTING | `documentation`, `good first issue`, `help wanted` |
| 009 | [009-narrow-exception-handling.md](009-narrow-exception-handling.md) | Narrow `except Exception` to specific types | `improvement`, `help wanted` |
| 010 | [010-skill-discovery-empty-or-missing-dir.md](010-skill-discovery-empty-or-missing-dir.md) | Handle missing/empty skill dirs in discovery | `bug`, `lampe-review`, `good first issue` |
| 011 | [011-feature-export-review-sarif.md](011-feature-export-review-sarif.md) | Export review results as SARIF | `enhancement`, `lampe-review`, `lampe-cli` |
| 012 | [012-feature-additional-workflows-roadmap.md](012-feature-additional-workflows-roadmap.md) | Additional workflows (PR size, diagrams) | `enhancement`, `lampe-cli`, `roadmap` |
| 013 | [013-ci-cache-uv-and-venv.md](013-ci-cache-uv-and-venv.md) | Cache uv/venv in GitHub Actions | `improvement`, `ci`, `good first issue` |
| 014 | [014-tests-aggregator-coverage.md](014-tests-aggregator-coverage.md) | Improve ReviewAggregator test coverage | `testing`, `lampe-review`, `good first issue` |
| 015 | [015-api-docstrings-public-api.md](015-api-docstrings-public-api.md) | Docstrings for public API (MkDocs) | `documentation`, `good first issue`, `help wanted` |
| 016 | [016-agentic-workflow-empty-diff.md](016-agentic-workflow-empty-diff.md) | Handle empty/large diff in agentic workflow | `bug`, `lampe-review` |
| 017 | [017-improvement-llm-retry-backoff.md](017-improvement-llm-retry-backoff.md) | Retry with backoff for LLM API failures | `improvement`, `lampe-review`, `lampe-describe` |
| 018 | [018-ci-dependency-audit.md](018-ci-dependency-audit.md) | Add dependency audit in CI (uv audit) | `improvement`, `ci`, `good first issue` |
| 019 | [019-validation-agent-malformed-json-parse.md](019-validation-agent-malformed-json-parse.md) | Fix malformed/truncated LLM JSON parse in validation agent | `bug`, `lampe-review` |

## Good first issues (for newcomers)

Issues that are small in scope and don’t require deep knowledge of the codebase:

- **001** – README typo
- **002** – pyproject.toml typo
- **003** – CONTRIBUTING workspace instructions
- **006** – MkDocs nav for agentic review
- **007** – Git version in README
- **008** – Good first issue guide in CONTRIBUTING
- **010** – Skill discovery edge cases
- **013** – CI cache for uv
- **014** – Aggregator tests
- **015** – Public API docstrings
- **018** – CI dependency audit

You can tag these with `good first issue` when creating them in GitHub so contributors can filter easily.
