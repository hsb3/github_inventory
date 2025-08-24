FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

ARG TZ
ENV TZ="$TZ"

ARG CLAUDE_CODE_VERSION=latest
ARG GIT_DELTA_VERSION=0.18.2
ARG ZSH_IN_DOCKER_VERSION=1.2.0

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Node.js for Claude Code
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# Set up environment
ENV UV_CACHE_DIR=/tmp/uv-cache
ENV PYTHONPATH=/workspace/src
ENV DEVCONTAINER=true
ENV SHELL=/bin/zsh
ENV EDITOR=nano
ENV VISUAL=nano

# Install enhanced development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    make \
    curl \
    less \
    procps \
    sudo \
    fzf \
    zsh \
    man-db \
    unzip \
    jq \
    nano \
    vim \
    dnsutils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install git-delta for better diffs
RUN ARCH=$(dpkg --print-architecture) && \
    wget "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
    dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
    rm "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"

# Persist bash history
RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" && \
    mkdir /commandhistory && \
    touch /commandhistory/.bash_history && \
    chown -R vscode /commandhistory

# Create workspace and cache directories
WORKDIR /workspace
RUN mkdir -p /tmp/uv-cache /home/vscode/.claude && \
    chown -R vscode:vscode /tmp/uv-cache /workspace /home/vscode/.claude

# Set up git safe directory (for when mounted)
RUN git config --global --add safe.directory /workspaces/github_inventory

# Install Claude Code as root (needs global permissions)
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

# Switch to vscode user for remaining setup
USER vscode

# Install zsh with oh-my-zsh and plugins
RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v${ZSH_IN_DOCKER_VERSION}/zsh-in-docker.sh)" -- \
    -p git \
    -p fzf \
    -a "source /usr/share/doc/fzf/examples/key-bindings.zsh" \
    -a "source /usr/share/doc/fzf/examples/completion.zsh" \
    -a "export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
    -x

# Copy Claude setup script
COPY setup-claude.sh /usr/local/bin/
USER root
RUN chmod +x /usr/local/bin/setup-claude.sh
USER vscode
