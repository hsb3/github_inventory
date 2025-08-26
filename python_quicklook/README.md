# Python Quick Look Tool

A comprehensive AST-based analyzer that provides detailed insights into Python project structure. Similar to how pytest discovers tests, this tool uses static analysis to inventory all classes, methods, and functions with their docstrings and signatures.

**✨ Now supports GitHub repositories!** Analyze any public GitHub repository directly from its URL.

## Project Structure

```
python_quicklook/
├── src/                          # Source code
│   ├── python_quicklook.py       # Main analysis engine
│   ├── project_context.py        # Project context analysis
│   ├── report_generator.py       # Report generation
│   ├── diagram_generator.py      # Diagram generation
│   ├── asset_manager.py          # Asset management
│   └── assets/                   # Generated diagram assets
├── tests/                        # Test suite
├── docs/                         # Project documentation
├── examples/                     # Example projects and usage
├── outputs/                      # Generated analysis reports
├── scripts/                      # Development utilities
└── temp/                         # Temporary files
```

## Usage

### Command Line Interface

```bash
# Local Analysis
python src/python_quicklook.py                    # Analyze current directory
python src/python_quicklook.py /path/to/project  # Analyze specific directory

# GitHub Repository Analysis
python src/python_quicklook.py github.com/user/repo          # Simple format
python src/python_quicklook.py https://github.com/user/repo  # Full URL
python src/python_quicklook.py user/repo                     # Minimal format

# Output Options
python src/python_quicklook.py pallets/flask --concise --output flask_analysis.md
python src/python_quicklook.py psf/requests --json --output stats.json

# Report Types
python src/python_quicklook.py src --concise    # Concise 5-minute overview
python src/python_quicklook.py src --json       # JSON statistics
python src/python_quicklook.py src              # Full detailed report
```

### Programmatic Usage

```python
import sys
sys.path.insert(0, 'src')
from src.python_quicklook import PythonQuickLook

# Local analysis
analyzer = PythonQuickLook('path/to/project')

# GitHub repository analysis
analyzer = PythonQuickLook('github.com/pallets/flask')
analyzer = PythonQuickLook('https://github.com/psf/requests')
analyzer = PythonQuickLook('user/repo')

# Run analysis
analyzer.analyze_project()

# Get statistics
stats = analyzer.get_statistics()
print(f"Found {stats['classes']} classes and {stats['functions']} functions")

# Generate report
from src.report_generator import MarkdownReportGenerator
generator = MarkdownReportGenerator(analyzer)
report = generator.generate()
```

## Testing

Run the test suite:

```bash
python -m pytest tests/ -v
```

Run specific test files:

```bash
python -m pytest tests/test_basic.py -v
python -m pytest tests/test_project_context.py -v
```

## Features

- **AST-based Analysis**: Deep static analysis of Python code structure
- **GitHub Repository Support**: Analyze any public GitHub repository directly from URL
- **Project Context**: Analyzes README, pyproject.toml, setup.py for project metadata
- **Visual Diagrams**: Mermaid diagrams that render natively in markdown
- **Concise Reports**: 5-minute overview focused on codebase understanding
- **CLI Detection**: Identifies command-line interfaces and entry points
- **Framework Detection**: Detects popular Python frameworks in use
- **Dependency Analysis**: Module relationships and circular dependency detection

## Requirements

### Core Requirements
- Python 3.7+

### GitHub Repository Analysis
- **GitHub CLI (`gh`)**: Required for GitHub repository access
  ```bash
  # Install GitHub CLI
  brew install gh        # macOS
  sudo apt install gh    # Ubuntu/Debian
  winget install GitHub.cli  # Windows

  # Authenticate (optional - enables private repos)
  gh auth login
  ```
- Optional: pylint and graphviz for diagram generation

## Development

The project uses a professional directory structure:

- **src/**: All source code is contained in the src directory
- **tests/**: Comprehensive test suite with proper import paths
- **outputs/**: Generated reports and analysis results
- **scripts/**: Development and utility scripts
- **docs/**: Project documentation
- **examples/**: Sample projects and usage examples

All tests use the pattern `sys.path.insert(0, 'src')` to properly import from the src directory.
