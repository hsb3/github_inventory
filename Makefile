# GitHub Inventory - Development Makefile

.PHONY: help setup clean example dev test quality

help:  ## Show this help message
	@echo "GitHub Inventory - Quick Commands"
	@echo "================================="
	@echo ""
	@echo "🚀 Getting Started:"
	@grep -E '^(setup|example):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🔧 Development:"
	@grep -E '^(dev|test|quality|clean):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "💡 For more options: gh-inventory --help"

setup:  ## Setup development environment
	uv venv --python 3.12
	uv sync --all-extras
	@echo "✅ Ready! Try: make example"

example:  ## Run example with sindresorhus (50 repos)
	mkdir -p docs/output_example
	uv run gh-inventory --user sindresorhus --limit 50 \
		--owned-csv docs/output_example/repos.csv \
		--starred-csv docs/output_example/starred_repos.csv \
		--report-md docs/output_example/README.md

dev:  ## Run development checks (format, lint, test)
	uv run ruff check --fix src/ tests/
	uv run black src/ tests/
	uv run pymarkdown --disable-rules MD013 fix --exclude TODO.md --exclude CLAUDE.md *.md
	uv run pytest tests/ -v
	@echo "✅ Development checks passed!"

test:  ## Run tests only
	uv run pytest tests/ -v

quality:  ## Run quality checks without fixes
	uv run ruff check src/ tests/
	uv run black --check src/ tests/
	uv run pymarkdown --disable-rules MD013 scan --exclude TODO.md --exclude CLAUDE.md *.md
	uv run pytest tests/ -v

clean:  ## Clean cache and output files
	rm -rf .pytest_cache/ .ruff_cache/ build/ dist/ *.egg-info/
	rm -f *.csv *.md docs/output_example/*.csv docs/output_example/*.md
	find . -type d -name __pycache__ -exec rm -rf {} +