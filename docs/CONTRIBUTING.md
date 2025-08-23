# Contributing to GitHub Inventory

Thank you for your interest in contributing to GitHub Inventory! This document provides guidelines for submitting issues and pull requests.

## Before You Start

- Check existing [issues](https://github.com/hsb3/github_inventory/issues) and [pull requests](https://github.com/hsb3/github_inventory/pulls) to avoid duplicates
- Make sure you have the GitHub CLI (`gh`) installed and authenticated
- Familiarize yourself with the project by reading the main [README.md](../README.md)

## Reporting Issues

### Bug Reports
When reporting bugs, please use the **Bug Report** template and include:

- **Environment details**: OS, Python version, GitHub CLI version
- **Reproduction steps**: Exact commands you ran
- **Expected vs actual behavior**: What you expected and what happened
- **GitHub CLI status**: Output of `gh auth status` (remove sensitive info)
- **Error output**: Full error messages and stack traces
- **Context**: Repository counts, .env file usage, etc.

Example bug report:
```bash
# Environment
OS: macOS 14.1
Python: 3.12.1
GitHub CLI: 2.40.1

# Command that failed
gh-inventory --user octocat --limit 10

# Error
Error: API rate limit exceeded
```

### Feature Requests
Use the **Feature Request** template and include:

- **Problem description**: What problem does this solve?
- **Proposed solution**: How should it work?
- **Example usage**: Show the command and expected output
- **GitHub API considerations**: Rate limits, permissions, etc.

### Questions
For usage questions, use the **Question** template or start a [Discussion](https://github.com/hsb3/github_inventory/discussions).

## Submitting Pull Requests

### Development Setup
1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/github_inventory.git
   cd github_inventory
   ```
3. Set up development environment:
   ```bash
   uv sync
   ```

### Making Changes
1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes following the project standards:
   - Use `uv run black src/ tests/` for formatting
   - Use `uv run ruff check src/ tests/` for linting
   - Use `uv run mypy src/` for type checking
   - Add tests for new functionality

3. Test your changes:
   ```bash
   # Run all tests
   uv run pytest tests/
   
   # Test CLI functionality
   uv run gh-inventory --help
   uv run gh-inventory --user hsb3 --limit 5 --no-report
   ```

4. Update documentation if needed

### Pull Request Guidelines
- Fill out the pull request template completely
- Include a clear description of the changes
- Reference any related issues
- Ensure all CI checks pass
- Keep PRs focused - one feature/fix per PR
- Use descriptive commit messages

### Code Standards
- **Python 3.12+** compatibility required
- **Type hints** for all new functions
- **Error handling** with informative messages
- **GitHub CLI integration** via subprocess calls
- **No hardcoded secrets** or tokens
- **Respect API rate limits**

### Testing Requirements
- All existing tests must pass
- Add tests for new functionality
- Test with different GitHub accounts
- Verify GitHub CLI authentication works
- Test edge cases (large repos, rate limits, network errors)

## Development Workflow

### Running Quality Checks
```bash
# Format code
make format

# Run linting
make lint

# Type checking
make typecheck

# Run all checks
make check
```

### Testing Different Scenarios
```bash
# Test with public user
uv run gh-inventory --user octocat --limit 10

# Test batch processing
uv run gh-inventory --batch config_example.json

# Test error handling
uv run gh-inventory --user nonexistent-user-12345
```

## GitHub CLI Considerations

This tool heavily relies on the GitHub CLI:
- Ensure `gh auth status` shows proper authentication
- Test with both public and private repositories
- Be aware of API rate limits (5,000 requests/hour for authenticated users)
- Consider pagination for users with many repositories

## Getting Help

- **Questions**: Use [Discussions](https://github.com/hsb3/github_inventory/discussions)
- **Bugs**: Create an [Issue](https://github.com/hsb3/github_inventory/issues) with the Bug Report template
- **Features**: Create an [Issue](https://github.com/hsb3/github_inventory/issues) with the Feature Request template

## Review Process

1. **Automated checks**: CI pipeline runs tests, linting, type checking
2. **Manual review**: Code owner (@hsb3) reviews changes
3. **Testing**: Verify functionality works as expected
4. **Merge**: Once approved, changes are merged to main branch

Thank you for contributing to GitHub Inventory!