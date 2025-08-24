#!/bin/bash

echo "🤖 Claude Code Setup"
echo "===================="

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
    echo "📱 For iPad/Codespaces users:"
    echo "   Authentication is stored in a persistent volume"
    echo "   You only need to authenticate once per Codespace"
fi

echo ""
echo "💡 Tip: Try 'claude --help' to see available commands"
