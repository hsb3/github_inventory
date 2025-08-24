#!/usr/bin/env bash

set -e

echo "🔧 Setting up development tools..."
echo "================================="

# Ensure Node.js and npm are available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found - this should be installed by the node feature"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm not found - this should be installed by the node feature"
    exit 1
fi

echo "✅ Node.js version: $(node --version)"
echo "✅ npm version: $(npm --version)"

# Install Claude Code CLI globally using npm (proven method from wandb/vibes)
echo "📦 Installing Claude Code CLI globally..."
npm install -g @anthropic-ai/claude-code@latest

# Verify installation
if command -v claude &> /dev/null; then
    echo "✅ Claude Code CLI installed successfully: $(claude --version)"
else
    echo "❌ Claude Code CLI installation failed"
    exit 1
fi

# Ensure correct permissions
echo "🔒 Setting up permissions..."
sudo chown -R vscode:vscode /tmp
mkdir -p /tmp/uv-cache /home/vscode/commandhistory
chown -R vscode:vscode /tmp/uv-cache /home/vscode/commandhistory

echo ""
echo "✅ Tool setup completed!"
echo "  📦 Claude Code CLI: $(which claude)"
echo "  🌐 Node.js: $(which node)"
echo "  📋 npm: $(which npm)"
echo ""
