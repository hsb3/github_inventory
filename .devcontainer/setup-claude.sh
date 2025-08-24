#!/bin/bash

echo "🤖 Claude Code Authentication Check"
echo "==================================="

# Verify Claude Code is installed
if ! command -v claude &> /dev/null; then
    echo "❌ Claude Code CLI not found"
    echo "This should have been installed by setup-tools.sh"
    echo "Try rebuilding the container or running manually:"
    echo "  npm install -g @anthropic-ai/claude-code@latest"
    exit 1
fi

echo "✅ Claude Code CLI ready: $(which claude)"
echo "📌 Version: $(claude --version 2>/dev/null || echo 'Unable to detect version')"

# Check if Claude Code is authenticated
if claude auth status >/dev/null 2>&1; then
    echo "✅ Claude Code is already authenticated"
    claude auth status 2>/dev/null || echo "Authentication status available"
else
    echo "⚠️  Claude Code is not authenticated yet"
    echo ""
    echo "🔐 To authenticate Claude Code:"
    echo "  1. Run: claude auth"
    echo "  2. Follow the browser authentication flow"
    echo "  3. Authentication persists across container rebuilds"
    echo ""
fi

echo ""
echo "🚀 Quick start commands:"
echo "  claude --help     # Show all available commands"
echo "  claude auth       # Authenticate (if needed)"
echo "  claude            # Start interactive Claude session"
echo ""
