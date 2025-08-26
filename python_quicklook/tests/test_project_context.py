"""
Comprehensive tests for the project_context module.
Tests all analyzer classes and their functionality.
"""

import ast
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the modules to test
from src.project_context import (
    CLICommand,
    CLIDetector,
    EntryPoint,
    FrameworkDetector,
    ProjectContextAnalyzer,
    ProjectDependency,
    ProjectMetadata,
    ProjectStructure,
    ProjectStructureAnalyzer,
    PyProjectAnalyzer,
    READMEAnalyzer,
    READMEInfo,
    SetupPyAnalyzer,
)


class TestProjectDependency:
    """Test ProjectDependency dataclass."""

    def test_init_minimal(self):
        dep = ProjectDependency(name="requests")
        assert dep.name == "requests"
        assert dep.version_spec is None
        assert dep.is_optional is False
        assert dep.group == "main"
        assert dep.extras == []

    def test_init_full(self):
        dep = ProjectDependency(
            name="pytest",
            version_spec=">=6.0.0",
            is_optional=True,
            group="dev",
            extras=["extra1", "extra2"]
        )
        assert dep.name == "pytest"
        assert dep.version_spec == ">=6.0.0"
        assert dep.is_optional is True
        assert dep.group == "dev"
        assert dep.extras == ["extra1", "extra2"]


class TestEntryPoint:
    """Test EntryPoint dataclass."""

    def test_init_minimal(self):
        ep = EntryPoint(name="myapp", module_path="myapp.cli", function_name="main")
        assert ep.name == "myapp"
        assert ep.module_path == "myapp.cli"
        assert ep.function_name == "main"
        assert ep.description is None
        assert ep.entry_type == "console_script"

    def test_init_full(self):
        ep = EntryPoint(
            name="myapp-gui",
            module_path="myapp.gui",
            function_name="start",
            description="GUI application",
            entry_type="gui_script"
        )
        assert ep.name == "myapp-gui"
        assert ep.module_path == "myapp.gui"
        assert ep.function_name == "start"
        assert ep.description == "GUI application"
        assert ep.entry_type == "gui_script"


class TestCLICommand:
    """Test CLICommand dataclass."""

    def test_init_minimal(self):
        cmd = CLICommand(name="test", module_path="test.cli", function_name="main")
        assert cmd.name == "test"
        assert cmd.module_path == "test.cli"
        assert cmd.function_name == "main"
        assert cmd.arguments == []
        assert cmd.options == []
        assert cmd.description is None
        assert cmd.parent_command is None


class TestPyProjectAnalyzer:
    """Test PyProjectAnalyzer class."""

    def test_analyze_missing_file(self):
        """Test behavior when pyproject.toml doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = PyProjectAnalyzer(Path(tmpdir))
            result = analyzer.analyze()
            assert result is None

    def test_analyze_basic_project(self):
        """Test analysis of basic pyproject.toml."""
        toml_content = '''
[project]
name = "test-project"
version = "1.0.0"
description = "A test project"
authors = [{name = "Test Author", email = "test@example.com"}]
license = {text = "MIT"}
requires-python = ">=3.8"
keywords = ["test", "example"]
classifiers = ["Programming Language :: Python :: 3"]

[project.urls]
Homepage = "https://example.com"
Repository = "https://github.com/user/project"

[project.scripts]
myapp = "myproject.cli:main"

[project.gui-scripts]
myapp-gui = "myproject.gui:start"
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            pyproject_path = tmpdir / "pyproject.toml"
            pyproject_path.write_text(toml_content)

            analyzer = PyProjectAnalyzer(tmpdir)
            result = analyzer.analyze()

            assert result is not None
            assert result.name == "test-project"
            assert result.version == "1.0.0"
            assert result.description == "A test project"
            assert result.author == "Test Author"
            assert result.author_email == "test@example.com"
            assert result.license == "MIT"
            assert result.python_requires == ">=3.8"
            assert result.keywords == ["test", "example"]
            assert result.classifiers == ["Programming Language :: Python :: 3"]
            assert result.homepage == "https://example.com"
            assert result.repository == "https://github.com/user/project"

            # Check entry points
            assert len(result.entry_points) == 2
            console_script = next(ep for ep in result.entry_points if ep.entry_type == "console_script")
            assert console_script.name == "myapp"
            assert console_script.module_path == "myproject.cli"
            assert console_script.function_name == "main"

            gui_script = next(ep for ep in result.entry_points if ep.entry_type == "gui_script")
            assert gui_script.name == "myapp-gui"
            assert gui_script.module_path == "myproject.gui"
            assert gui_script.function_name == "start"

    def test_analyze_with_dependencies(self):
        """Test analysis with dependencies."""
        toml_content = '''
[project]
name = "test-project"
dependencies = [
    "requests>=2.25.0",
    "click",
    "pydantic>=1.8.0; python_version>='3.8'"
]

[project.optional-dependencies]
dev = ["pytest>=6.0", "black", "mypy"]
docs = ["sphinx>=4.0"]
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            pyproject_path = tmpdir / "pyproject.toml"
            pyproject_path.write_text(toml_content)

            analyzer = PyProjectAnalyzer(tmpdir)
            result = analyzer.analyze()

            assert result is not None
            assert len(result.dependencies) == 3

            # Check main dependencies
            requests_dep = next(dep for dep in result.dependencies if dep.name == "requests")
            assert requests_dep.version_spec == ">=2.25.0"
            assert requests_dep.group == "main"

            click_dep = next(dep for dep in result.dependencies if dep.name == "click")
            assert click_dep.version_spec is None

            pydantic_dep = next(dep for dep in result.dependencies if dep.name == "pydantic")
            assert pydantic_dep.version_spec == ">=1.8.0"

            # Check optional dependencies
            assert "dev" in result.optional_dependencies
            assert "docs" in result.optional_dependencies

            dev_deps = result.optional_dependencies["dev"]
            assert len(dev_deps) == 3
            pytest_dep = next(dep for dep in dev_deps if dep.name == "pytest")
            assert pytest_dep.version_spec == ">=6.0"
            assert pytest_dep.group == "dev"

    def test_parse_entry_point(self):
        """Test entry point parsing."""
        analyzer = PyProjectAnalyzer(Path("."))

        # Test with function name
        module, func = analyzer._parse_entry_point("myproject.cli:main")
        assert module == "myproject.cli"
        assert func == "main"

        # Test without function name (defaults to main)
        module, func = analyzer._parse_entry_point("myproject.cli")
        assert module == "myproject.cli"
        assert func == "main"

    def test_extract_license_formats(self):
        """Test different license format extraction."""
        analyzer = PyProjectAnalyzer(Path("."))

        # String format
        assert analyzer._extract_license("MIT") == "MIT"

        # Dictionary with text
        assert analyzer._extract_license({"text": "MIT"}) == "MIT"

        # Dictionary with file
        assert analyzer._extract_license({"file": "LICENSE"}) == "LICENSE"

        # None
        assert analyzer._extract_license(None) is None


class TestSetupPyAnalyzer:
    """Test SetupPyAnalyzer class."""

    def test_analyze_missing_file(self):
        """Test behavior when setup.py doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = SetupPyAnalyzer(Path(tmpdir))
            result = analyzer.analyze()
            assert result is None

    def test_analyze_basic_setup(self):
        """Test analysis of basic setup.py."""
        setup_content = '''
from setuptools import setup

setup(
    name="test-project",
    version="1.0.0",
    description="A test project",
    author="Test Author",
    author_email="test@example.com",
    url="https://example.com",
    python_requires=">=3.8",
    install_requires=["requests", "click>=7.0"],
)
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            setup_path = tmpdir / "setup.py"
            setup_path.write_text(setup_content)

            analyzer = SetupPyAnalyzer(tmpdir)
            result = analyzer.analyze()

            assert result is not None
            assert result.name == "test-project"
            assert result.version == "1.0.0"
            assert result.description == "A test project"
            assert result.author == "Test Author"
            assert result.author_email == "test@example.com"
            assert result.homepage == "https://example.com"
            assert result.python_requires == ">=3.8"

            # Check dependencies
            assert len(result.dependencies) == 2
            dep_names = [dep.name for dep in result.dependencies]
            assert "requests" in dep_names
            assert "click>=7.0" in dep_names

    def test_find_setup_call(self):
        """Test finding setup() call in AST."""
        analyzer = SetupPyAnalyzer(Path("."))

        # Test direct setup() call
        code = "setup(name='test')"
        tree = ast.parse(code)
        call = analyzer._find_setup_call(tree)
        assert call is not None
        assert isinstance(call.func, ast.Name)
        assert call.func.id == "setup"

        # Test setuptools.setup() call
        code = "setuptools.setup(name='test')"
        tree = ast.parse(code)
        call = analyzer._find_setup_call(tree)
        assert call is not None
        assert isinstance(call.func, ast.Attribute)
        assert call.func.attr == "setup"

    def test_extract_string_value(self):
        """Test string value extraction from AST nodes."""
        analyzer = SetupPyAnalyzer(Path("."))

        # Test Constant node (Python 3.8+)
        node = ast.parse('"test"').body[0].value
        value = analyzer._extract_string_value(node)
        assert value == "test"

        # Test None value
        node = ast.parse('None').body[0].value
        value = analyzer._extract_string_value(node)
        assert value is None

    def test_extract_list_values(self):
        """Test list value extraction from AST nodes."""
        analyzer = SetupPyAnalyzer(Path("."))

        # Test list of strings
        node = ast.parse('["a", "b", "c"]').body[0].value
        values = analyzer._extract_list_values(node)
        assert values == ["a", "b", "c"]

        # Test empty list
        node = ast.parse('[]').body[0].value
        values = analyzer._extract_list_values(node)
        assert values == []

        # Test non-list
        node = ast.parse('"not a list"').body[0].value
        values = analyzer._extract_list_values(node)
        assert values == []


class TestREADMEAnalyzer:
    """Test READMEAnalyzer class."""

    def test_analyze_missing_file(self):
        """Test behavior when no README exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = READMEAnalyzer(Path(tmpdir))
            result = analyzer.analyze()
            assert result is None

    def test_find_readme_files(self):
        """Test finding various README file names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create README.md
            readme_path = tmpdir / "README.md"
            readme_path.write_text("# Test Project")

            analyzer = READMEAnalyzer(tmpdir)
            found_path = analyzer._find_readme()
            assert found_path == readme_path

            # Test case insensitive
            readme_path.unlink()
            (tmpdir / "README.txt").write_text("Test Project")

            analyzer = READMEAnalyzer(tmpdir)
            found_path = analyzer._find_readme()
            assert found_path.name == "README.txt"

    def test_analyze_markdown_readme(self):
        """Test analysis of Markdown README."""
        markdown_content = '''# Test Project

This is a test project for demonstration purposes.

## Installation

```bash
pip install test-project
```

## Usage

```python
import test_project
test_project.run()
```

## Features

- Feature 1
- Feature 2

[![Build Status](https://travis-ci.org/user/project.svg?branch=main)](https://travis-ci.org/user/project)

Check out the [documentation](https://docs.example.com) for more info.
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            readme_path = tmpdir / "README.md"
            readme_path.write_text(markdown_content)

            analyzer = READMEAnalyzer(tmpdir)
            result = analyzer.analyze()

            assert result is not None
            assert result.file_path == "README.md"
            assert result.title == "Test Project"
            assert len(result.sections) == 4  # Installation, Usage, Features
            assert "installation" in result.sections
            assert "usage" in result.sections
            assert "features" in result.sections
            assert len(result.badges) > 0
            assert len(result.links) > 0

            # Check that installation section was captured
            assert result.installation_section is not None
            assert "pip install" in result.installation_section

            # Check that usage section was captured
            assert result.usage_section is not None
            assert "import test_project" in result.usage_section

    def test_analyze_rst_readme(self):
        """Test analysis of reStructuredText README."""
        rst_content = '''Test Project
============

This is a test project written in reStructuredText format.

Installation
------------

Use pip to install the package.

Usage
-----

Import the module and use it.
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            readme_path = tmpdir / "README.rst"
            readme_path.write_text(rst_content)

            analyzer = READMEAnalyzer(tmpdir)
            result = analyzer.analyze()

            assert result is not None
            assert result.file_path == "README.rst"
            assert result.title == "Test Project"
            assert len(result.sections) > 0

    def test_analyze_plain_text_readme(self):
        """Test analysis of plain text README."""
        text_content = '''Test Project

This is a simple plain text README file.

It contains basic information about the project.
Installation instructions and usage examples would go here.
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            readme_path = tmpdir / "README.txt"
            readme_path.write_text(text_content)

            analyzer = READMEAnalyzer(tmpdir)
            result = analyzer.analyze()

            assert result is not None
            assert result.file_path == "README.txt"
            assert result.title == "Test Project"
            assert result.description is not None
            assert "simple plain text README" in result.description


class TestProjectStructureAnalyzer:
    """Test ProjectStructureAnalyzer class."""

    def test_analyze_basic_structure(self):
        """Test analysis of basic project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create basic structure
            (tmpdir / "myproject").mkdir(parents=True)
            (tmpdir / "myproject" / "__init__.py").touch()
            (tmpdir / "tests").mkdir(parents=True)
            (tmpdir / "tests" / "test_main.py").touch()
            (tmpdir / "docs").mkdir(parents=True)
            (tmpdir / "docs" / "index.md").touch()
            (tmpdir / "pyproject.toml").touch()
            (tmpdir / "requirements.txt").touch()
            (tmpdir / "Makefile").touch()

            analyzer = ProjectStructureAnalyzer(tmpdir)
            result = analyzer.analyze()

            assert result.is_package is True
            assert result.has_src_layout is False
            assert "myproject" in result.package_dirs
            assert "tests" in result.test_dirs
            assert "docs" in result.doc_dirs
            assert "pyproject.toml" in result.config_files
            assert "requirements.txt" in result.config_files
            assert "Makefile" in result.config_files
            assert result.has_requirements_txt is True
            assert result.has_makefile is True

    def test_analyze_src_layout(self):
        """Test analysis of src layout structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create src layout
            (tmpdir / "src" / "myproject").mkdir(parents=True)
            (tmpdir / "src" / "myproject" / "__init__.py").touch()
            (tmpdir / "test").mkdir(parents=True)
            (tmpdir / "test" / "test_main.py").touch()

            analyzer = ProjectStructureAnalyzer(tmpdir)
            result = analyzer.analyze()

            assert result.has_src_layout is True
            assert result.is_package is True
            assert "src/myproject" in result.package_dirs

    def test_analyze_docker_setup(self):
        """Test detection of Docker setup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            (tmpdir / "Dockerfile").touch()
            (tmpdir / "docker-compose.yml").touch()

            analyzer = ProjectStructureAnalyzer(tmpdir)
            result = analyzer.analyze()

            assert result.has_dockerfile is True
            assert result.has_docker_compose is True

    def test_analyze_dependency_tools(self):
        """Test detection of dependency management tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            (tmpdir / "poetry.lock").touch()
            (tmpdir / "Pipfile").touch()

            analyzer = ProjectStructureAnalyzer(tmpdir)
            result = analyzer.analyze()

            assert result.has_poetry_lock is True
            assert result.has_pipfile is True


class TestCLIDetector:
    """Test CLIDetector class."""

    def test_is_potential_cli_module(self):
        """Test detection of potential CLI modules."""
        # Mock module objects
        cli_module = MagicMock()
        cli_module.name = "cli"
        cli_module.functions = []

        main_module = MagicMock()
        main_module.name = "main"
        main_module.functions = []

        main_func_module = MagicMock()
        main_func_module.name = "utils"
        main_func = MagicMock()
        main_func.name = "main"
        main_func_module.functions = [main_func]

        regular_module = MagicMock()
        regular_module.name = "utils"
        regular_module.functions = []

        detector = CLIDetector(Path("."), [])

        assert detector._is_potential_cli_module(cli_module) is True
        assert detector._is_potential_cli_module(main_module) is True
        assert detector._is_potential_cli_module(main_func_module) is True
        assert detector._is_potential_cli_module(regular_module) is False

    def test_analyze_argparse(self):
        """Test detection of argparse usage."""
        code = '''
import argparse

def main():
    parser = argparse.ArgumentParser(description="Test CLI tool")
    parser.add_argument("--verbose", help="Enable verbose mode")
    args = parser.parse_args()
'''

        tree = ast.parse(code)
        detector = CLIDetector(Path("."), [])
        commands = detector._analyze_argparse(tree, "test_module")

        assert len(commands) == 1
        assert commands[0].name == "main"
        assert commands[0].module_path == "test_module"
        assert commands[0].description == "Test CLI tool"

    def test_analyze_click(self):
        """Test detection of Click framework usage."""
        code = '''
import click

@click.command()
def hello():
    """A simple greeting command."""
    click.echo("Hello!")
'''

        tree = ast.parse(code)
        detector = CLIDetector(Path("."), [])
        commands = detector._analyze_click(tree, "test_module")

        assert len(commands) == 1
        assert commands[0].name == "hello"
        assert commands[0].module_path == "test_module"
        assert commands[0].description == "A simple greeting command."

    def test_analyze_typer(self):
        """Test detection of Typer framework usage."""
        code = '''
import typer

def main(name: str, count: int = 1):
    """Say hello to someone."""
    for _ in range(count):
        typer.echo(f"Hello {name}!")
'''

        tree = ast.parse(code)
        detector = CLIDetector(Path("."), [])
        commands = detector._analyze_typer(tree, "test_module")

        assert len(commands) == 1
        assert commands[0].name == "main"
        assert commands[0].module_path == "test_module"
        assert commands[0].description == "Say hello to someone."


class TestFrameworkDetector:
    """Test FrameworkDetector class."""

    def test_detect_web_frameworks(self):
        """Test detection of web frameworks."""
        deps = [
            ProjectDependency(name="flask"),
            ProjectDependency(name="django"),
            ProjectDependency(name="fastapi"),
        ]

        detector = FrameworkDetector(Path("."), [], deps)
        frameworks, patterns = detector.detect_frameworks()

        assert "Flask" in frameworks
        assert "Django" in frameworks
        assert "FastAPI" in frameworks

    def test_detect_cli_frameworks(self):
        """Test detection of CLI frameworks."""
        deps = [
            ProjectDependency(name="click"),
            ProjectDependency(name="typer"),
        ]

        detector = FrameworkDetector(Path("."), [], deps)
        frameworks, patterns = detector.detect_frameworks()

        assert "Click" in frameworks
        assert "Typer" in frameworks

    def test_detect_data_science_frameworks(self):
        """Test detection of data science frameworks."""
        deps = [
            ProjectDependency(name="pandas"),
            ProjectDependency(name="numpy"),
            ProjectDependency(name="matplotlib"),
        ]

        detector = FrameworkDetector(Path("."), [], deps)
        frameworks, patterns = detector.detect_frameworks()

        assert "Pandas" in frameworks
        assert "NumPy" in frameworks
        assert "Matplotlib" in frameworks

    def test_detect_patterns_from_structure(self):
        """Test detection of patterns from project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "requirements.txt").touch()
            (tmpdir / "Dockerfile").touch()
            (tmpdir / "docker-compose.yml").touch()

            # Mock modules
            test_module = MagicMock()
            test_module.name = "test_utils"

            cli_module = MagicMock()
            cli_module.name = "cli"

            api_module = MagicMock()
            api_module.name = "api"

            modules = [test_module, cli_module, api_module]

            detector = FrameworkDetector(tmpdir, modules, [])
            frameworks, patterns = detector.detect_frameworks()

            assert "Testing" in patterns
            assert "Command Line Interface" in patterns
            assert "API" in patterns
            assert "pip requirements" in patterns
            assert "Docker" in patterns
            assert "Docker Compose" in patterns


class TestProjectContextAnalyzer:
    """Test ProjectContextAnalyzer integration."""

    def test_analyze_complete_project(self):
        """Test analysis of a complete project setup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create pyproject.toml
            toml_content = '''
[project]
name = "test-project"
version = "1.0.0"
description = "A comprehensive test project"
authors = [{name = "Test Author", email = "test@example.com"}]
dependencies = ["click", "requests"]

[project.scripts]
myapp = "myproject.cli:main"
'''
            (tmpdir / "pyproject.toml").write_text(toml_content)

            # Create README
            readme_content = '''# Test Project

A comprehensive test project.

## Installation

pip install test-project

## Usage

Run with `myapp --help`.
'''
            (tmpdir / "README.md").write_text(readme_content)

            # Create project structure
            (tmpdir / "myproject").mkdir(parents=True)
            (tmpdir / "myproject" / "__init__.py").touch()
            (tmpdir / "tests").mkdir(parents=True)
            (tmpdir / "tests" / "__init__.py").touch()
            (tmpdir / "Dockerfile").touch()

            # Mock modules for CLI detection
            modules = []

            analyzer = ProjectContextAnalyzer(tmpdir)
            context = analyzer.analyze(modules)

            assert context.project_name == tmpdir.name
            assert context.root_path == str(tmpdir)

            # Check metadata
            assert context.metadata is not None
            assert context.metadata.name == "test-project"
            assert context.metadata.version == "1.0.0"
            assert context.metadata.description == "A comprehensive test project"

            # Check README
            assert context.readme_info is not None
            assert context.readme_info.title == "Test Project"

            # Check structure
            assert context.structure is not None
            assert context.structure.is_package is True
            assert context.structure.has_dockerfile is True

            # Check frameworks (requires dependencies to be detected)
            # Framework detection works from dependencies
            dep_names = [dep.name for dep in context.metadata.dependencies]
            assert "click" in dep_names
            assert "requests" in dep_names

    def test_analyze_with_setup_py_fallback(self):
        """Test fallback to setup.py when pyproject.toml is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create setup.py
            setup_content = '''
from setuptools import setup

setup(
    name="legacy-project",
    version="0.1.0",
    description="A legacy setup.py project",
)
'''
            (tmpdir / "setup.py").write_text(setup_content)

            analyzer = ProjectContextAnalyzer(tmpdir)
            context = analyzer.analyze()

            assert context.metadata is not None
            assert context.metadata.name == "legacy-project"
            assert context.metadata.version == "0.1.0"
