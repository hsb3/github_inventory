# GitHub Workflows

This document explains the GitHub Actions workflows configured for this repository and their purposes.

## Overview

The repository uses 5 GitHub Actions workflows to automate testing, security, branch protection, dependency management, and AI-assisted code review.

## Workflows

### 1. CI (`ci.yml`)

**Purpose:** Continuous Integration testing for all code changes

**Triggers:**

- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop` branches

**What it does:**

- **Multi-version testing:** Tests against Python 3.12 and 3.13
- **Code quality:** Runs ruff linting and formatting checks
- **Formatting:** Validates black code formatting
- **Type checking:** Runs mypy for static type analysis
- **Unit tests:** Executes pytest test suite
- **CLI validation:** Tests that the `ghscan` command installs and runs
- **Security:** Runs ruff security checks (S-prefixed rules)

**Why we need it:** Ensures all code changes maintain quality standards and don't break existing functionality before merging.

### 2. Branch Protection (`branch-protection.yml`)

**Purpose:** Automatically maintains GitHub branch protection rules

**Triggers:**

- Weekly schedule: Sundays at 6 AM UTC
- Manual trigger via `workflow_dispatch`

**What it does:**

- Enforces required status checks (Python 3.12/3.13 tests + security)
- Requires 1 approving review for PRs
- Dismisses stale reviews when new commits are pushed
- Prevents force pushes and branch deletion
- Requires conversation resolution before merging

**Why we need it:** GitHub branch protection rules can drift over time or be accidentally modified. This workflow ensures they stay consistent with our security and quality requirements.

### 3. Claude Code Review (`claude-code-review.yml`)

**Purpose:** Automated AI code review using Anthropic's Claude

**Triggers:**

- Pull request opened or updated
- Only runs on Python files, config files, and build scripts

**What it does:**

- Reviews code quality and PEP 8 compliance
- Checks type hints and mypy compliance
- Validates test coverage for new functionality
- Reviews security considerations for CLI input handling
- Analyzes performance implications for GitHub API calls
- Verifies error handling and user feedback
- **Critical:** Runs test suite to ensure all tests pass
- Provides constructive feedback and improvement suggestions

**Why we need it:** Provides consistent, thorough code reviews focusing on Python best practices, security, and testing. Especially valuable for catching test failures and ensuring new code follows project conventions.

**Note:** This workflow requires the workflow file to match the version on the main branch for security reasons. It may fail on PRs that modify the workflow file itself.

### 4. Claude Code (`claude.yml`)

**Purpose:** Interactive AI assistant triggered by @claude mentions

**Triggers:**

- Issue comments containing `@claude`
- Pull request review comments containing `@claude`
- Pull request reviews containing `@claude`
- Issues opened with `@claude` in title or body

**What it does:**

- Responds to @claude mentions from authorized users (owner, members, collaborators)
- Can run development commands (make, uv, pytest, linting tools)
- Provides code assistance following project guidelines
- **Critical requirement:** Always updates tests when changing function signatures
- Runs full test suite before considering changes complete
- Follows project coding standards and pre-commit hooks

**Why we need it:** Enables AI-assisted development and issue resolution. Particularly useful for code reviews, bug fixes, and development guidance while maintaining test integrity.

**Security:** Only responds to authorized repository users and has limited tool access.

### 5. Dependabot Updates

**Purpose:** Automated dependency updates

**Triggers:**

- Scheduled by Dependabot configuration (not visible in workflows directory)

**What it does:**

- Creates PRs for dependency updates
- Monitors for security vulnerabilities
- Updates Python packages and GitHub Actions

**Why we need it:** Keeps dependencies current and secure without manual intervention.

## Workflow Dependencies

The workflows are designed to work together:

1. **CI** validates all changes and provides status checks
2. **Branch Protection** requires CI to pass before merging
3. **Claude Code Review** provides additional automated review
4. **Claude Code** assists with development and fixes
5. **Dependabot** keeps dependencies updated, triggering CI for validation

## Security Considerations

- Claude workflows only respond to authorized users
- Branch protection prevents unauthorized changes to main
- Security scans run on every PR
- Workflow files must match main branch to prevent malicious modifications

## Troubleshooting

### Claude Workflows Failing

If Claude workflows fail with "workflow file must exist and have identical content to the version on the repository's default branch":

1. This is expected when modifying workflow files in PRs
2. Merge workflow changes to main first
3. Test Claude functionality in subsequent PRs

### CI Failures

- Check that all pre-commit hooks pass locally: `make hooks`
- Run tests locally: `make test`
- Verify formatting: `make format`

### Branch Protection Issues

- The weekly branch protection workflow will restore proper settings
- Manual trigger available if immediate restoration needed

## Development Commands

```bash
# List all workflows
gh workflow list

# Check recent runs
gh run list --limit 10

# View specific run details
gh run view <run-id>

# Manually trigger branch protection
gh workflow run "Branch Protection"

# Test workflow syntax
gh workflow view "CI" --yaml > /dev/null
```
