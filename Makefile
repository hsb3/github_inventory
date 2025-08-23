# GitHub Inventory - Development Makefile

.PHONY: help setup install hooks format lint typecheck test clean
.DEFAULT_GOAL := help

help:  ## Show this help message
	@echo "GitHub Inventory - Development Commands"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

check-uv:
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }

install: check-uv  ## Install dependencies only
	@test -d .venv || uv venv --python 3.12
	uv sync --all-extras

hooks: install  ## Install and run pre-commit hooks
	uv run pre-commit install
	uv run pre-commit run --all-files

format: install  ## Format code
	uv run ruff format src/ tests/
	uv run black src/ tests/

lint: install  ## Lint code
	uv run ruff check src/ tests/

typecheck: install  ## Type check code
	uv run mypy src/

test: install  ## Run tests
	uv run pytest tests/ -v

setup: install hooks test  ## Setup complete development environment
	@echo "✅ Development environment ready!"

clean:  ## Clean cache and build files
	rm -rf .pytest_cache/ .ruff_cache/ build/ dist/ *.egg-info/ .mypy_cache/ .venv/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
