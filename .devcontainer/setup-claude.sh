#!/bin/bash

echo "🤖 Claude Code Setup"
echo "===================="

# Verify Claude Code is installed
if ! command -v claude &> /dev/null; then
    echo "❌ Claude Code CLI not found"
    echo "This should have been installed automatically by the devcontainer feature."
    echo "Please rebuild the container or install manually with:"
    echo "  npm install -g @anthropic-ai/claude-code@latest"
    exit 1
fi

echo "✅ Claude Code CLI found: $(which claude)"
echo "📌 Version: $(claude --version 2>/dev/null || echo 'Unable to detect version')"

# Check if Claude Code is authenticated
if claude auth status >/dev/null 2>&1; then
    echo "✅ Claude Code is already authenticated"
    claude auth status
else
    echo "❌ Claude Code is not authenticated"
    echo ""
    echo "To authenticate Claude Code:"
    echo "1. Run: claude auth"
    echo "2. Follow the authentication flow"
    echo "3. Your authentication will persist across container rebuilds"
    echo ""
    echo "📱 For Codespaces users:"
    echo "   - Authentication is stored in a persistent volume"
    echo "   - You only need to authenticate once per Codespace"
    echo "   - The authentication survives container rebuilds"
fi

echo ""
echo "💡 Quick start:"
echo "  claude --help     # See available commands"
echo "  claude auth       # Authenticate if needed"
echo "  claude            # Start interactive session"
echo ""
