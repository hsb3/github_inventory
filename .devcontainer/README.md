# Dev Container Configuration

This directory contains the development container configuration optimized for both **local Docker** and **GitHub Codespaces** environments.

## 🎯 2025 Best Practices

This configuration follows modern devcontainer best practices:

- **Feature-based installation**: Uses official devcontainer features instead of custom Dockerfile
- **Universal compatibility**: Works identically in local Docker and GitHub Codespaces
- **Latest versions**: Uses LTS Node.js, latest GitHub CLI, and latest Claude Code
- **Proper separation**: Separate scripts for project setup vs Claude setup
- **Persistent storage**: Command history and Claude authentication survive rebuilds

## 🏗️ Architecture

### Base Image

- `mcr.microsoft.com/devcontainers/python:1-3.12-bullseye` - Official Python 3.12 image

### Features Used

1. **Node.js LTS** - `ghcr.io/devcontainers/features/node:1`
   - Latest LTS version with npm
   - Includes build dependencies for native modules

2. **GitHub CLI** - `ghcr.io/devcontainers/features/github-cli:1`
   - Latest version installed directly from GitHub releases

3. **Claude Code CLI** - `ghcr.io/anthropics/devcontainer-features/claude-code:1`
   - Official Anthropic feature for Claude Code installation
   - Automatically handles Node.js dependencies

4. **Common Utils** - `ghcr.io/devcontainers/features/common-utils:2`
   - Zsh with Oh My Zsh configuration
   - Essential development tools

### Setup Scripts

- **`setup-project.sh`**: Python environment and project dependencies
- **`setup-claude.sh`**: Claude Code verification and authentication guidance

## 🚀 Usage

### Local Development (VS Code + Docker)

1. Install "Dev Containers" extension in VS Code
2. Open project in VS Code
3. Click "Reopen in Container" when prompted
4. Wait for automatic setup to complete

### GitHub Codespaces

1. Go to your GitHub repository
2. Click "Code" → "Codespaces" → "Create codespace"
3. Wait for automatic setup to complete
4. Start coding immediately

## ⚡ Quick Start

After the container starts:

```bash
# Activate Python environment
source .venv/bin/activate

# Test the project
ghscan --help

# Authenticate Claude Code (if needed)
claude auth

# Start using Claude Code
claude
```

## 🔧 Environment Details

### Python Environment

- Python 3.12 with uv package manager
- Virtual environment at `.venv/`
- All project dependencies installed
- Pre-commit hooks configured

### Development Tools

- Zsh with Oh My Zsh (default shell)
- GitHub CLI authenticated through VS Code
- Node.js LTS with npm
- Claude Code CLI ready to authenticate

### VS Code Extensions

- Python development (Python, mypy, ruff, black)
- File support (TOML, YAML, Markdown)
- Makefile tools

### Persistent Data

- **Command history**: Zsh history persists across rebuilds
- **Claude authentication**: Stored in dedicated volume
- **Git configuration**: Mounted from host system

## 🐛 Troubleshooting

### Container Build Issues

```bash
# Clear Docker cache and rebuild
docker system prune -a
# In VS Code: "Dev Containers: Rebuild Container Without Cache"
```

### Claude Code Issues

```bash
# Check installation
claude --version
which claude

# Re-authenticate
claude auth

# Manual installation (if needed)
npm install -g @anthropic-ai/claude-code@latest
```

### Python Environment Issues

```bash
# Check virtual environment
source .venv/bin/activate
python --version
pip list

# Rebuild Python environment
make setup
# OR manually: uv sync --all-extras
```

### Permission Issues

```bash
# Fix ownership (run as root in container)
sudo chown -R vscode:vscode /tmp/uv-cache /home/vscode
```

## 🔄 Updates

To update the configuration:

1. **Update features**: Change version numbers in `devcontainer.json`
2. **Rebuild**: Use "Dev Containers: Rebuild Container" in VS Code
3. **Clean rebuild**: Use "Dev Containers: Rebuild Container Without Cache"

## 📝 Configuration Files

- `devcontainer.json`: Main configuration using features
- `setup-project.sh`: Python project initialization
- `setup-claude.sh`: Claude Code setup and verification
- `Dockerfile.old`: Legacy Dockerfile (backup)

This configuration ensures consistent, fast setup across all development environments.
