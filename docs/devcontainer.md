# Dev Container Configuration

This project includes a comprehensive development container setup that provides a consistent, fully-configured development environment with all necessary tools pre-installed.

## Overview

The dev container is based on the official Microsoft Python 3.12 image and includes:

- Python 3.12 with uv package manager
- GitHub CLI (gh) for repository interactions
- Claude Code CLI for AI assistance
- Enhanced shell environment with Zsh and Oh My Zsh
- VS Code extensions and settings for Python development
- Persistent storage for configuration and history

## Container Features

### Base Environment

- **Base Image**: `mcr.microsoft.com/devcontainers/python:1-3.12-bullseye`
- **Python Version**: 3.12
- **Package Manager**: uv (latest version from ghcr.io/astral-sh/uv)
- **Node.js**: v20.x (for Claude Code support)

### Development Tools

#### Core Tools
- Git with git-delta for enhanced diffs
- Make for task automation
- GitHub CLI for repository operations
- Claude Code CLI for AI-powered development assistance

#### Shell Environment
- Zsh with Oh My Zsh framework
- fzf for fuzzy finding
- Persistent command history across container rebuilds
- Pre-configured shell plugins (git, fzf)

#### Editors
- nano (default)
- vim
- VS Code integration

### VS Code Extensions

The container automatically installs the following extensions:

- **Python Development**:
  - `ms-python.python` - Python language support
  - `ms-python.mypy-type-checker` - Type checking
  - `charliermarsh.ruff` - Fast Python linter
  - `ms-python.black-formatter` - Code formatting

- **File Support**:
  - `tamasfe.even-better-toml` - TOML file support
  - `redhat.vscode-yaml` - YAML file support
  - `yzhang.markdown-all-in-one` - Markdown editing
  - `davidanson.vscode-markdownlint` - Markdown linting
  - `ms-vscode.makefile-tools` - Makefile support

### Persistent Storage

The dev container uses Docker volumes to persist data across container rebuilds:

1. **Command History**: Bash/Zsh history persisted in a dedicated volume
2. **Claude Configuration**: Claude Code authentication stored persistently
3. **Git Config**: Mounted from host system for seamless git operations

## Environment Variables

The container sets the following environment variables:

```bash
UV_CACHE_DIR=/tmp/uv-cache          # uv package cache location
PYTHONPATH=/workspace/src            # Python module search path
DEVCONTAINER=true                    # Indicates dev container environment
CLAUDE_CONFIG_DIR=/home/vscode/.claude  # Claude Code config location
SHELL=/bin/zsh                       # Default shell
EDITOR=nano                          # Default text editor
VISUAL=nano                          # Visual editor
```

## Automatic Setup

When the container starts, it automatically:

1. Runs `make setup` to:
   - Create Python virtual environment
   - Install all dependencies
   - Configure pre-commit hooks
   - Run initial tests

2. Executes `setup-claude.sh` to:
   - Check Claude Code authentication status
   - Provide authentication instructions if needed
   - Display helpful tips for using Claude Code

## VS Code Settings

The container applies Python-specific VS Code settings:

- **Interpreter**: Automatically uses `.venv/bin/python`
- **Formatting**: Black formatter with 88-character line length
- **Linting**: Ruff enabled with organize imports on save
- **Type Checking**: mypy enabled
- **Auto-formatting**: Format on save enabled for Python files
- **File Exclusions**: Hides cache directories (`__pycache__`, `.pytest_cache`, etc.)
- **Terminal**: Zsh as default shell

## Using the Dev Container

### With VS Code

1. Install the "Dev Containers" extension in VS Code
2. Open the project folder
3. Click "Reopen in Container" when prompted
4. Wait for the container to build and setup to complete

### With GitHub Codespaces

1. Click "Code" → "Codespaces" → "Create codespace on main"
2. The dev container configuration is automatically applied
3. All tools and dependencies are pre-installed

### Authentication

#### GitHub CLI
The container includes GitHub CLI. Authenticate with:

```bash
gh auth login
```

#### Claude Code
Claude Code requires one-time authentication:

```bash
claude auth
```

Authentication is stored persistently and survives container rebuilds.

## Customization

### Build Arguments

The Dockerfile accepts several build arguments for customization:

- `TZ`: Timezone (defaults to system timezone or America/Los_Angeles)
- `CLAUDE_CODE_VERSION`: Claude Code version (defaults to latest)
- `GIT_DELTA_VERSION`: git-delta version (defaults to 0.18.2)
- `ZSH_IN_DOCKER_VERSION`: Zsh setup script version (defaults to 1.2.0)

### Adding Tools

To add additional tools, modify:

1. **System packages**: Update the `apt-get install` section in the Dockerfile
2. **VS Code extensions**: Add to the `extensions` array in devcontainer.json
3. **Python packages**: Update pyproject.toml and rebuild

## Troubleshooting

### Container Build Issues

If the container fails to build:

1. Check Docker daemon is running
2. Clear Docker cache: `docker system prune -a`
3. Rebuild without cache: "Dev Containers: Rebuild Container Without Cache"

### Python Environment Issues

If Python packages aren't found:

1. Ensure virtual environment is activated
2. Check PYTHONPATH: `echo $PYTHONPATH`
3. Reinstall dependencies: `make setup`

### Claude Code Authentication

If Claude Code isn't working:

1. Check status: `claude auth status`
2. Re-authenticate: `claude auth`
3. Verify config directory: `ls -la ~/.claude`

### Persistent Data Loss

If history or settings are lost:

1. Check volume mounts: `docker volume ls | grep github-inventory`
2. Ensure proper permissions: volumes are owned by vscode user
3. Rebuild container preserving volumes

## Performance Tips

1. **Use uv for packages**: Faster than pip for dependency installation
2. **Cache management**: Clear `/tmp/uv-cache` if disk space is low
3. **Extension sync**: Disable VS Code settings sync if experiencing conflicts
4. **Resource allocation**: Increase Docker memory for large codebases

## Security Notes

- Git config is mounted read-only from host
- Claude authentication is isolated per container
- No secrets are stored in the image
- Container runs as non-root user (vscode)
