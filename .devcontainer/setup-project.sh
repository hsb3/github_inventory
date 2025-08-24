#!/bin/bash

set -e

echo "🐍 Setting up Python project environment..."
echo "============================================="

# Install uv if not already available
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Verify uv installation
echo "✅ uv version: $(uv --version)"

# Run project setup using Makefile
echo "🔧 Running project setup..."
if [ -f "Makefile" ] && make -n setup &> /dev/null; then
    make setup
else
    echo "⚠️  Makefile setup target not found, running manual setup..."

    # Create virtual environment
    echo "📁 Creating Python virtual environment..."
    uv venv --python 3.12

    # Install dependencies
    echo "📦 Installing dependencies..."
    uv sync --all-extras

    # Install pre-commit hooks if available
    if [ -f ".pre-commit-config.yaml" ]; then
        echo "🎣 Setting up pre-commit hooks..."
        source .venv/bin/activate
        pre-commit install
    fi

    # Run tests to verify setup
    echo "🧪 Running tests to verify setup..."
    source .venv/bin/activate
    if [ -d "tests" ]; then
        python -m pytest tests/ -v --tb=short || echo "⚠️  Some tests failed, but setup continues..."
    fi
fi

echo ""
echo "✅ Python project setup completed!"
echo ""
echo "💡 Next steps:"
echo "  1. Activate virtual environment: source .venv/bin/activate"
echo "  2. Run the tool: ghscan --help"
echo "  3. Authenticate Claude Code when prompted"
echo ""
