# GitHub Inventory - Development Makefile

.PHONY: help setup install install-analysis install-global hooks format lint typecheck test clean example dev-build dev-up
.DEFAULT_GOAL := help

help:  ## Show this help message
	@echo "GitHub Inventory - Development Commands"
	@echo "======================================"
	@echo ""
	@echo "\033[1m🚀 Getting Started:\033[0m"
	@echo "  \033[36msetup\033[0m           Complete development environment setup (recommended)"
	@echo "  \033[36minstall-global\033[0m  Install ghscan command globally (uv tool install)"
	@echo ""
	@echo "\033[1m🔧 Development:\033[0m"
	@echo "  \033[36minstall\033[0m         Install dependencies in virtual environment"
	@echo "  \033[36minstall-analysis\033[0m Install additional analysis tools (prospector, pylint, etc.)"
	@echo "  \033[36mhooks\033[0m           Install and run pre-commit hooks (format, lint, type check)"
	@echo "  \033[36mtest\033[0m            Run all tests with coverage report"
	@echo ""
	@echo "\033[1m🎯 Code Quality:\033[0m"
	@echo "  \033[36mformat\033[0m          Format code with ruff and black"
	@echo "  \033[36mlint\033[0m            Lint code with ruff"
	@echo "  \033[36mtypecheck\033[0m       Type check code with mypy"
	@echo ""
	@echo "\033[1m📝 Usage Examples:\033[0m"
	@echo "  \033[36mexample\033[0m         Run example ghscan command (sindresorhus, 50 repo limit)"
	@echo ""
	@echo "\033[1m🐳 Dev Container:\033[0m"
	@echo "  \033[36mdev-build\033[0m       Build dev container with proper naming"
	@echo "  \033[36mdev-up\033[0m          Start dev container environment"
	@echo ""
	@echo "\033[1m🧹 Maintenance:\033[0m"
	@echo "  \033[36mclean\033[0m           Clean cache and build files (including .venv)"
	@echo ""
	@echo "\033[1m💡 Quick Start:\033[0m"
	@echo "  \033[33mmake setup\033[0m      # For development work"
	@echo "  \033[33mmake install-global\033[0m # For global ghscan command"
	@echo "  \033[33mmake install-analysis\033[0m # For advanced analysis tools (branch-specific)"
	@echo "  \033[33mghscan --help\033[0m   # See all available options"

check-uv:
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }

check-env: check-uv  ## Check if virtual environment and dependencies are ready
	@test -d .venv || { echo "❌ Virtual environment not found. Run 'make install' first."; exit 1; }
	@test -f .venv/pyvenv.cfg || { echo "❌ Virtual environment incomplete. Run 'make install' first."; exit 1; }

install: check-uv  ## Install dependencies in virtual environment
	@echo "📦 Setting up virtual environment and dependencies..."
	@test -d .venv || uv venv --python 3.12
	uv sync --all-extras
	uv pip install -e .
	@echo "✅ Dependencies installed! Run 'source .venv/bin/activate' to use ghscan locally."

install-analysis: check-uv  ## Install additional analysis tools (prospector, pylint, etc.)
	@echo "🔬 Installing advanced analysis tools..."
	@test -d .venv || { echo "❌ Virtual environment not found. Run 'make install' first."; exit 1; }
	uv sync --group analysis
	@echo "✅ Analysis tools installed! Use prospector, pylint, pdoc, etc."

install-global: check-uv  ## Install ghscan command globally with uv tool
	@echo "🌍 Installing ghscan globally..."
	uv tool install .
	@echo "✅ ghscan installed globally! Try: ghscan --help"

hooks: install  ## Install and run pre-commit hooks (format, lint, type check)
	@echo "🪝 Setting up and running pre-commit hooks..."
	uv run pre-commit install
	uv run pre-commit run --all-files

format: check-env  ## Format code with ruff and black
	@echo "🎨 Formatting code..."
	uv run ruff format src/ tests/
	uv run black src/ tests/

lint: check-env  ## Lint code with ruff
	@echo "🔍 Linting code..."
	uv run ruff check src/ tests/

typecheck: check-env  ## Type check code with mypy
	@echo "🔬 Type checking code..."
	uv run mypy src/

test: check-env  ## Run all tests with coverage report
	@echo "🧪 Running tests with coverage..."
	uv run pytest tests/ --cov=src/github_inventory --cov-report=term-missing -v

setup: install hooks test  ## Complete development environment setup (recommended)
	@echo ""
	@echo "✅ Development environment ready!"
	@echo "💡 To use ghscan locally: source .venv/bin/activate && ghscan --help"
	@echo "🌍 To install globally instead: make install-global"

example: check-env  ## Run example ghscan command (sindresorhus, 50 repo limit)
	@echo "📝 Running example command..."
	uv run ghscan --user sindresorhus --limit 50 --no-report

dev-build:  ## Build dev container with proper naming
	@echo "🐳 Building dev container..."
	@command -v devcontainer >/dev/null 2>&1 || { echo "❌ devcontainer CLI not found. Install with: npm install -g @devcontainers/cli"; exit 1; }
	devcontainer build --workspace-folder . --image-name github-inventory-dev:latest
	@echo "✅ Dev container built successfully!"

dev-up:  ## Start dev container environment
	@echo "🚀 Starting dev container..."
	@command -v devcontainer >/dev/null 2>&1 || { echo "❌ devcontainer CLI not found. Install with: npm install -g @devcontainers/cli"; exit 1; }
	devcontainer up --workspace-folder .
	@echo "✅ Dev container started! Use VS Code 'Attach to Running Container' to connect."

clean:  ## Clean cache and build files (including .venv)
	@echo "🧹 Cleaning up..."
	rm -rf .pytest_cache/ .ruff_cache/ build/ dist/ *.egg-info/ .mypy_cache/ .venv/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete!"
