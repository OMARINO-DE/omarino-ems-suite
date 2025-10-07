FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# Install additional tools
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    postgresql-client \
    redis-tools \
    httpie \
    jq \
    vim \
    curl \
    git \
    make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install pnpm for Node.js projects
RUN npm install -g pnpm@latest

# Install Python tools
RUN pip install --no-cache-dir \
    black \
    ruff \
    pytest \
    pytest-cov \
    mypy \
    pre-commit

# Install MkDocs for documentation
RUN pip install --no-cache-dir \
    mkdocs \
    mkdocs-material \
    mkdocs-mermaid2-plugin

# Set working directory
WORKDIR /workspaces/omarino-ems-suite
