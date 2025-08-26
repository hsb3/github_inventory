# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python Quick Look Tool is a comprehensive AST-based static analyzer that provides detailed insights into Python project structure. It generates rich markdown reports with embedded visual diagrams for both local directories and GitHub repositories.

**Key Capabilities:**
- Analyzes Python projects without code execution using AST parsing
- Supports both local directories and GitHub URLs (`github.com/username/reponame`)
- Generates comprehensive markdown reports with embedded PNG diagrams
- Creates visual class diagrams and dependency graphs
- Extracts project context from README, pyproject.toml, setup.py files

## Development Commands

### Running the Tool

```bash
# Analyze current directory
python src/python_quicklook.py

# Analyze specific directory
python src/python_quicklook.py /path/to/project

# Save output to file
python src/python_quicklook.py src --output outputs/analysis.md

# Analyze GitHub repository
python src/python_quicklook.py github.com/user/repo
python src/python_quicklook.py https://github.com/user/repo
python src/python_quicklook.py user/repo
```

### Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_basic.py -v
python -m pytest tests/test_project_context.py -v
python -m pytest tests/test_main_integration.py -v

# Run with coverage (if installed)
python -m pytest tests/ -v --cov=src --cov-report=html
```

**Test Structure:** All tests use `sys.path.insert(0, str(Path(__file__).parent.parent / "src"))` to properly import from the src directory.

### Code Quality

This project inherits quality tools from the parent project:
- **Formatting**: `ruff format` and `black`
- **Linting**: `ruff check`
- **Type checking**: `mypy`
- Run from parent directory: `make format`, `make lint`, `make typecheck`

## Architecture Overview

### Core Components

**Analysis Engine (`src/python_quicklook.py`)**
- Main `PythonQuickLook` class handles both local and GitHub targets
- AST-based parsing extracts classes, functions, methods, imports
- Supports initialization patterns: `PythonQuickLook(".")`, `PythonQuickLook("github.com/user/repo")`
- Coordinates analysis across all specialized modules

**Context Analysis (`src/project_context.py`)**
- `ProjectContextAnalyzer` extracts project metadata from README, pyproject.toml, setup.py
- Identifies entry points, CLI commands, dependencies
- Provides project purpose and usage examples

**Dependency Analysis (`src/dependency_analyzer.py`)**
- `DependencyAnalyzer` builds import dependency graphs
- Maps module relationships and identifies circular dependencies
- Integrates with visualization components

**CLI Analysis (`src/cli_analyzer.py`)**
- `CLIAnalyzer` parses argparse configurations
- Extracts command-line interface patterns and usage
- Identifies main entry points and subcommands

**Configuration Analysis (`src/configuration_analyzer.py`)**
- `ConfigurationAnalyzer` parses project configuration files
- Extracts environment variables, setup requirements
- Analyzes build and deployment configurations

**GitHub Support (`src/github_support.py`)**
- `GitHubSupport` handles repository cloning via GitHub CLI (`gh`)
- Parses GitHub URLs in multiple formats
- Manages temporary directories with automatic cleanup
- Requires `gh` CLI authentication

### Visualization Pipeline

**Diagram Generation (`src/diagram_generator.py`)**
- `DiagramGenerator` creates class diagrams using pyreverse/graphviz
- Generates PNG files for markdown embedding
- Handles dependency installation and fallback scenarios

**Mermaid Integration (`src/mermaid_generator.py`)**
- Creates mermaid.js diagrams for workflow visualization
- Renders dependency graphs and data flow diagrams
- Converts mermaid to PNG for report embedding

**Asset Management (`src/asset_manager.py`)**
- `AssetManager` handles `assets/` folder creation and management
- Manages relative path embedding (`![](assets/diagram.png)`)
- Coordinates between diagram generators and report output

### Report Generation

**Markdown Reports (`src/report_generator.py`)**
- `MarkdownReportGenerator` creates comprehensive single-file reports
- Embeds visual diagrams using relative asset paths
- Supports multiple docstring formats (Google, NumPy, Sphinx)
- Implements collapsible sections and rich formatting

**Concise Reports (`src/concise_report_generator.py`)**
- Alternative report format for quick project overviews
- Focused on essential project structure and key components
- Useful for rapid assessment and onboarding

## Data Flow Architecture

```
Input (Local Directory / GitHub URL)
    ↓
Target Resolution (local path or GitHub cloning)
    ↓
File Discovery (Python files, ignore patterns)
    ↓
Parallel Analysis:
├── AST Analysis → Code Inventory (classes, functions, methods)
├── Context Analysis → Project Metadata (README, configs)
├── Dependency Analysis → Import Relationships
├── CLI Analysis → Command-line Interfaces
└── Configuration Analysis → Build/Deploy Configs
    ↓
Visual Generation:
├── Pyreverse → Class Diagrams (PNG)
└── Mermaid → Dependency Graphs (PNG)
    ↓
Asset Management → assets/ folder + relative paths
    ↓
Report Generation → Single Markdown File
    ↓
Output: report.md + assets/ folder
```

## Key Implementation Patterns

**Modular Analysis Design:**
- Each analyzer operates independently on the discovered modules
- Results are aggregated in the main `PythonQuickLook` class
- Enables parallel analysis and easy extension

**Import Path Handling:**
- Uses try/except import patterns for both direct execution and module imports
- Test files use `sys.path.insert(0, 'src')` for proper imports
- Supports both standalone and integrated usage

**GitHub Integration:**
- Leverages `gh` CLI for secure authentication and repository access
- Temporary cloning with automatic cleanup via context managers
- Supports multiple GitHub URL formats and private repositories

**Visualization Pipeline:**
- Generates diagrams as PNG files in dedicated `assets/` folder
- Uses relative paths for markdown embedding portability
- Graceful degradation when visualization dependencies unavailable

## Dependencies and Requirements

**Core Requirements:**
- Python 3.7+ (uses `ast.unparse` and other modern features)
- Standard library only for basic analysis functionality

**Optional Dependencies:**
- `pylint` + `graphviz` for class diagram generation (pyreverse)
- `gh` CLI for GitHub repository support
- Inherits quality tools from parent project (`ruff`, `mypy`, `black`)

**External Tool Integration:**
- GitHub CLI (`gh`) must be installed and authenticated for GitHub URL support
- Graphviz must be installed for visual diagram generation
- Uses subprocess calls for external tool integration

## Testing Strategy

**Test Organization:**
- `tests/test_*.py` files cover individual components
- `tests/test_main_integration.py` provides end-to-end testing
- Each test file includes proper import path setup

**Test Patterns:**
- Unit tests for AST parsing, context extraction, dependency analysis
- Integration tests for complete analysis workflows
- Mock GitHub repositories for testing without network dependencies

**Coverage Areas:**
- AST parsing accuracy across Python language features
- Context extraction from various project configurations
- GitHub URL parsing and repository handling
- Report generation with embedded diagrams
