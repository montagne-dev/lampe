##@ Utility
.PHONY: help
help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: i
i: ## Install dependencies
	uv sync

.PHONY: c
clean: ## Remove build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -exec rm -rf {} +
c: clean ## Remove build artifacts and cache

.PHONY: clean-venv
clean-venv: clean ## Remove .venv directory and clean build artifacts
	rm -rf .venv/

.PHONY: clean-all
clean-all: clean-venv ## Remove build artifacts and cache
	rm -rf uv.lock

.PHONY: tl
tl: ## Run pytests and lint
	uv run pytest
	uv run pyright

.PHONY: t
t: ## Run tests
	uv run pytest tests/ packages/**/tests/ -vv

.PHONY: ut
ut: ## Run unit tests
	uv run pytest

.PHONY: it
it: ## Run integration tests
	uv run pytest tests/integration packages/**/tests/integration
