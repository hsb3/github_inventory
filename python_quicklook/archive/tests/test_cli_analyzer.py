"""
Tests for CLI pattern analyzer functionality.
"""

import ast
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.cli_analyzer import (
    CLIAnalyzer,
    CLIFramework,
    CLIInterface,
    CLICommand,
    CLIArgument,
    ArgumentType,
    ArgparseAnalyzer,
    ClickAnalyzer,
    TyperAnalyzer,
    FireAnalyzer,
    CLIPatternDetector
)
from src.python_quicklook import ModuleInfo


class TestCLIPatternDetector:
    """Test CLI framework detection patterns."""

    def test_detect_framework_from_imports(self):
        """Test framework detection from import statements."""
        detector = CLIPatternDetector()

        # Create mock module with various imports
        module = ModuleInfo(
            name="test_module",
            path="test.py",
            docstring="Test module",
            imports=[
                "import argparse",
                "import click",
                "from typer import Typer",
                "import fire",
                "from docopt import docopt"
            ]
        )

        detected = detector.detect_framework_from_imports(module)

        expected = {
            CLIFramework.ARGPARSE,
            CLIFramework.CLICK,
            CLIFramework.TYPER,
            CLIFramework.FIRE,
            CLIFramework.DOCOPT
        }

        assert detected == expected

    def test_detect_framework_from_ast_argparse(self):
        """Test argparse detection from AST."""
        detector = CLIPatternDetector()

        code = """
import argparse

def main():
    parser = argparse.ArgumentParser(description='Test CLI')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
"""

        tree = ast.parse(code)
        detected = detector.detect_framework_from_ast(tree)

        assert CLIFramework.ARGPARSE in detected

    def test_detect_framework_from_ast_click(self):
        """Test Click detection from AST decorators."""
        detector = CLIPatternDetector()

        code = """
import click

@click.command()
@click.option('--verbose', is_flag=True)
def main(verbose):
    pass
"""

        tree = ast.parse(code)
        detected = detector.detect_framework_from_ast(tree)

        assert CLIFramework.CLICK in detected

    def test_detect_framework_from_ast_fire(self):
        """Test Fire detection from AST."""
        detector = CLIPatternDetector()

        code = """
import fire

def main():
    pass

if __name__ == '__main__':
    fire.Fire(main)
"""

        tree = ast.parse(code)
        detected = detector.detect_framework_from_ast(tree)

        assert CLIFramework.FIRE in detected


class TestArgparseAnalyzer:
    """Test argparse pattern analysis."""

    def test_analyze_simple_argparse(self):
        """Test analysis of simple argparse CLI."""
        analyzer = ArgparseAnalyzer()

        code = """
import argparse

def main():
    parser = argparse.ArgumentParser(description='Test CLI tool')
    parser.add_argument('input_file', help='Input file path')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--format', choices=['json', 'yaml'], default='json')

    args = parser.parse_args()
    print(f"Processing {args.input_file}")

if __name__ == '__main__':
    main()
"""

        module = ModuleInfo(name="test_cli", path="test_cli.py", docstring="Test CLI")
        tree = ast.parse(code)

        interface = analyzer.analyze_module(module, tree)

        assert interface is not None
        assert interface.framework == CLIFramework.ARGPARSE
        assert interface.main_function == "main"
        assert len(interface.global_arguments) == 4

        # Check positional argument
        input_arg = next(arg for arg in interface.global_arguments if arg.name == "input_file")
        assert input_arg.arg_type == ArgumentType.POSITIONAL
        assert input_arg.help_text == "Input file path"

        # Check optional argument with short form
        output_arg = next(arg for arg in interface.global_arguments if arg.name == "--output")
        assert output_arg.arg_type == ArgumentType.OPTIONAL
        assert output_arg.help_text == "Output file path"

        # Check flag
        verbose_arg = next(arg for arg in interface.global_arguments if arg.name == "--verbose")
        assert verbose_arg.arg_type == ArgumentType.FLAG
        assert verbose_arg.action == "store_true"

        # Check choices
        format_arg = next(arg for arg in interface.global_arguments if arg.name == "--format")
        assert format_arg.choices == ["json", "yaml"]
        assert format_arg.default_value == "json"

    def test_no_argparse_patterns(self):
        """Test that analyzer returns None when no argparse patterns found."""
        analyzer = ArgparseAnalyzer()

        code = """
def main():
    print("Hello, world!")
"""

        module = ModuleInfo(name="simple", path="simple.py", docstring="Simple module")
        tree = ast.parse(code)

        interface = analyzer.analyze_module(module, tree)

        assert interface is None


class TestClickAnalyzer:
    """Test Click pattern analysis."""

    def test_analyze_simple_click(self):
        """Test analysis of simple Click CLI."""
        analyzer = ClickAnalyzer()

        code = """
import click

@click.group()
@click.version_option()
def cli():
    \"\"\"Test CLI application.\"\"\"
    pass

@cli.command()
@click.argument('input_file')
@click.option('--output', '-o', help='Output file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def process(input_file, output, verbose):
    \"\"\"Process the input file.\"\"\"
    if verbose:
        click.echo(f"Processing {input_file}")

if __name__ == '__main__':
    cli()
"""

        module = ModuleInfo(name="click_cli", path="click_cli.py", docstring="Click CLI")
        tree = ast.parse(code)

        interface = analyzer.analyze_module(module, tree)

        assert interface is not None
        assert interface.framework == CLIFramework.CLICK
        assert len(interface.commands) == 2  # cli group and process command

        # Find the process command
        process_cmd = next(cmd for cmd in interface.commands if cmd.name == "process")
        assert process_cmd.description == "Process the input file."
        assert len(process_cmd.arguments) == 3

        # Check argument types
        arg_types = {arg.name: arg.arg_type for arg in process_cmd.arguments}
        assert ArgumentType.POSITIONAL in arg_types.values()
        assert ArgumentType.OPTIONAL in arg_types.values()
        assert ArgumentType.FLAG in arg_types.values()

    def test_click_command_only(self):
        """Test analysis of single Click command (not group)."""
        analyzer = ClickAnalyzer()

        code = """
import click

@click.command()
@click.option('--count', default=1, help='Number of greetings.')
@click.argument('name')
def hello(count, name):
    \"\"\"Simple program that greets NAME for a total of COUNT times.\"\"\"
    for i in range(count):
        click.echo(f'Hello {name}!')

if __name__ == '__main__':
    hello()
"""

        module = ModuleInfo(name="hello_cli", path="hello.py", docstring="Hello CLI")
        tree = ast.parse(code)

        interface = analyzer.analyze_module(module, tree)

        assert interface is not None
        assert len(interface.commands) == 1

        hello_cmd = interface.commands[0]
        assert hello_cmd.name == "hello"
        assert hello_cmd.description == "Simple program that greets NAME for a total of COUNT times."
        assert len(hello_cmd.arguments) == 2


class TestTyperAnalyzer:
    """Test Typer pattern analysis."""

    def test_analyze_simple_typer(self):
        """Test analysis of simple Typer CLI."""
        analyzer = TyperAnalyzer()

        code = """
import typer
from typing import Optional

app = typer.Typer()

@app.command()
def hello(
    name: str = typer.Argument(..., help="The name to greet"),
    count: int = typer.Option(1, help="Number of greetings"),
    formal: bool = typer.Option(False, help="Use formal greeting")
):
    \"\"\"Greet someone.\"\"\"
    greeting = "Good day" if formal else "Hello"
    for _ in range(count):
        typer.echo(f"{greeting}, {name}!")

if __name__ == "__main__":
    app()
"""

        module = ModuleInfo(name="typer_cli", path="typer_cli.py", docstring="Typer CLI")
        tree = ast.parse(code)

        interface = analyzer.analyze_module(module, tree)

        assert interface is not None
        assert interface.framework == CLIFramework.TYPER
        assert len(interface.commands) == 1

        hello_cmd = interface.commands[0]
        assert hello_cmd.name == "hello"
        assert hello_cmd.description == "Greet someone."
        assert len(hello_cmd.arguments) == 3

        # Check type annotations
        name_arg = next(arg for arg in hello_cmd.arguments if arg.name == "name")
        assert name_arg.type_name == "str"


class TestFireAnalyzer:
    """Test Fire pattern analysis."""

    def test_analyze_fire_function(self):
        """Test analysis of Fire with a single function."""
        analyzer = FireAnalyzer()

        code = """
import fire

def calculate(x: float, y: float, operation: str = "add"):
    \"\"\"Perform arithmetic operations on two numbers.

    Args:
        x: First number
        y: Second number
        operation: Operation to perform (add, subtract, multiply, divide)

    Returns:
        The result of the operation
    \"\"\"
    if operation == "add":
        return x + y
    elif operation == "subtract":
        return x - y
    elif operation == "multiply":
        return x * y
    elif operation == "divide":
        return x / y
    else:
        raise ValueError(f"Unknown operation: {operation}")

if __name__ == "__main__":
    fire.Fire(calculate)
"""

        module = ModuleInfo(name="fire_cli", path="fire_cli.py", docstring="Fire CLI")
        tree = ast.parse(code)

        interface = analyzer.analyze_module(module, tree)

        assert interface is not None
        assert interface.framework == CLIFramework.FIRE
        assert len(interface.commands) == 1

        calc_cmd = interface.commands[0]
        assert calc_cmd.name == "calculate"
        assert "Perform arithmetic operations" in calc_cmd.description
        assert len(calc_cmd.arguments) == 3

    def test_analyze_fire_class(self):
        """Test analysis of Fire with a class."""
        analyzer = FireAnalyzer()

        code = """
import fire

class Calculator:
    \"\"\"A simple calculator class.\"\"\"

    def add(self, x: float, y: float):
        \"\"\"Add two numbers.\"\"\"
        return x + y

    def subtract(self, x: float, y: float):
        \"\"\"Subtract second number from first.\"\"\"
        return x - y

    def _private_method(self):
        \"\"\"This should not be a command.\"\"\"
        pass

if __name__ == "__main__":
    fire.Fire(Calculator)
"""

        module = ModuleInfo(name="calc_fire", path="calc_fire.py", docstring="Calculator Fire")
        tree = ast.parse(code)

        interface = analyzer.analyze_module(module, tree)

        assert interface is not None
        assert len(interface.commands) == 2  # add and subtract (not _private_method)

        command_names = {cmd.name for cmd in interface.commands}
        assert command_names == {"add", "subtract"}

        add_cmd = next(cmd for cmd in interface.commands if cmd.name == "add")
        assert add_cmd.description == "Add two numbers."
        assert len(add_cmd.arguments) == 2  # x and y (self is filtered out)


class TestCLIAnalyzer:
    """Test main CLI analyzer coordination."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def test_analyze_multiple_frameworks(self):
        """Test analysis of project with multiple CLI frameworks."""
        analyzer = CLIAnalyzer(self.temp_path)

        # Create modules with different CLI frameworks
        argparse_module = ModuleInfo(
            name="argparse_cli",
            path="argparse_cli.py",
            docstring="Argparse CLI",
            imports=["import argparse"]
        )

        click_module = ModuleInfo(
            name="click_cli",
            path="click_cli.py",
            docstring="Click CLI",
            imports=["import click"]
        )

        # Create temporary files
        (self.temp_path / "argparse_cli.py").write_text("""
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

if __name__ == '__main__':
    main()
""")

        (self.temp_path / "click_cli.py").write_text("""
import click

@click.command()
@click.option('--count', default=1)
def hello(count):
    \"\"\"Say hello.\"\"\"
    for _ in range(count):
        click.echo('Hello!')

if __name__ == '__main__':
    hello()
""")

        modules = [argparse_module, click_module]
        result = analyzer.analyze(modules)

        assert len(result.detected_frameworks) == 2
        assert CLIFramework.ARGPARSE in result.detected_frameworks
        assert CLIFramework.CLICK in result.detected_frameworks
        assert len(result.interfaces) == 2

    def test_analyze_with_entry_points(self):
        """Test analysis including entry point extraction."""
        analyzer = CLIAnalyzer(self.temp_path)

        # Create pyproject.toml with entry points
        (self.temp_path / "pyproject.toml").write_text("""
[project.scripts]
mycli = "mypackage.cli:main"
mytool = "mypackage.tools:run"
""")

        modules = []
        result = analyzer.analyze(modules)

        assert "mycli" in result.entry_points
        assert result.entry_points["mycli"] == "mypackage.cli:main"
        assert "mytool" in result.entry_points
        assert result.entry_points["mytool"] == "mypackage.tools:run"

    def test_analyze_configuration_files(self):
        """Test detection of configuration files."""
        analyzer = CLIAnalyzer(self.temp_path)

        # Create various config files
        (self.temp_path / "config.yaml").touch()
        (self.temp_path / ".env").touch()
        (self.temp_path / "settings.json").touch()

        modules = []
        result = analyzer.analyze(modules)

        expected_configs = {"config.yaml", ".env", "settings.json"}
        assert set(result.configuration_files) >= expected_configs

    def test_analyze_environment_variables(self):
        """Test extraction of environment variable usage."""
        analyzer = CLIAnalyzer(self.temp_path)

        # Create module that uses environment variables
        module = ModuleInfo(
            name="env_cli",
            path="env_cli.py",
            docstring="CLI with env vars",
            imports=["import os"]
        )

        (self.temp_path / "env_cli.py").write_text("""
import os

def main():
    api_key = os.environ['API_KEY']
    debug = os.getenv('DEBUG', 'false')
    log_level = os.environ.get('LOG_LEVEL', 'info')

    print(f"API Key: {api_key}")
    print(f"Debug: {debug}")
    print(f"Log Level: {log_level}")

if __name__ == '__main__':
    main()
""")

        modules = [module]
        result = analyzer.analyze(modules)

        expected_vars = {"API_KEY", "DEBUG", "LOG_LEVEL"}
        assert set(result.environment_variables) >= expected_vars

    def test_analyze_error_handling(self):
        """Test error handling for malformed files."""
        analyzer = CLIAnalyzer(self.temp_path)

        # Create module with syntax error
        module = ModuleInfo(
            name="broken_cli",
            path="broken_cli.py",
            docstring="Broken CLI",
            imports=["import argparse"]
        )

        (self.temp_path / "broken_cli.py").write_text("""
import argparse

def main():
    parser = argparse.ArgumentParser(
    # Missing closing parenthesis - syntax error
""")

        modules = [module]
        result = analyzer.analyze(modules)

        # Should handle error gracefully
        assert len(result.warnings) > 0 or len(result.errors) > 0

    def test_analyze_empty_project(self):
        """Test analysis of project with no CLI patterns."""
        analyzer = CLIAnalyzer(self.temp_path)

        module = ModuleInfo(
            name="simple",
            path="simple.py",
            docstring="Simple module",
            imports=[]
        )

        (self.temp_path / "simple.py").write_text("""
def add(x, y):
    \"\"\"Add two numbers.\"\"\"
    return x + y
""")

        modules = [module]
        result = analyzer.analyze(modules)

        assert len(result.detected_frameworks) == 0
        assert len(result.interfaces) == 0


class TestCLIArgumentFormatting:
    """Test CLI argument formatting for different argument types."""

    def test_positional_argument(self):
        """Test formatting of positional arguments."""
        arg = CLIArgument(
            name="input_file",
            arg_type=ArgumentType.POSITIONAL,
            help_text="Input file path",
            required=True
        )

        # Test that argument is created correctly
        assert arg.name == "input_file"
        assert arg.arg_type == ArgumentType.POSITIONAL
        assert arg.help_text == "Input file path"
        assert arg.required is True

    def test_optional_argument_with_forms(self):
        """Test optional arguments with short and long forms."""
        arg = CLIArgument(
            name="--output",
            arg_type=ArgumentType.OPTIONAL,
            help_text="Output file path",
            short_form="-o",
            long_form="--output",
            default_value="output.txt"
        )

        assert arg.short_form == "-o"
        assert arg.long_form == "--output"
        assert arg.default_value == "output.txt"

    def test_flag_argument(self):
        """Test flag arguments."""
        arg = CLIArgument(
            name="--verbose",
            arg_type=ArgumentType.FLAG,
            help_text="Enable verbose output",
            action="store_true"
        )

        assert arg.arg_type == ArgumentType.FLAG
        assert arg.action == "store_true"

    def test_argument_with_choices(self):
        """Test arguments with restricted choices."""
        arg = CLIArgument(
            name="--format",
            arg_type=ArgumentType.OPTIONAL,
            help_text="Output format",
            choices=["json", "yaml", "xml"],
            default_value="json"
        )

        assert arg.choices == ["json", "yaml", "xml"]
        assert arg.default_value == "json"


# Integration test using the existing integration test structure
class TestCLIAnalysisIntegration:
    """Integration tests for CLI analysis with existing project structure."""

    def test_cli_analysis_integration(self):
        """Test CLI analysis integration with the test project from integration tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a project with CLI components
            self._create_cli_test_project(tmpdir)

            # Import and test the integration
            from src.python_quicklook import PythonQuickLook
            from src.report_generator import MarkdownReportGenerator

            # Run analysis
            analyzer = PythonQuickLook(str(tmpdir))
            analyzer.analyze_project()

            # Verify CLI analysis was performed
            assert analyzer.cli_analysis is not None
            assert len(analyzer.cli_analysis.interfaces) > 0

            # Check that Click was detected
            assert CLIFramework.CLICK in analyzer.cli_analysis.detected_frameworks

            # Generate report and verify CLI section is included
            generator = MarkdownReportGenerator(analyzer)
            report = generator.generate()

            assert "🖥️ Command Line Interface" in report
            assert "Click Interface" in report
            assert "Entry Points" in report

    def _create_cli_test_project(self, tmpdir: Path) -> None:
        """Create a test project with CLI components."""
        # Create package structure
        package_dir = tmpdir / "testcli"
        package_dir.mkdir()

        (package_dir / "__init__.py").write_text('__version__ = "1.0.0"')

        # Create CLI module using Click
        (package_dir / "cli.py").write_text('''
"""CLI module for test project."""
import click

@click.group()
@click.version_option()
def cli():
    """Test CLI application."""
    pass

@cli.command()
@click.argument('input_file')
@click.option('--output', '-o', help='Output file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def process(input_file, output, verbose):
    """Process the input file."""
    if verbose:
        click.echo(f"Processing {input_file}")

    if output:
        click.echo(f"Output will be written to {output}")

@cli.command()
@click.option('--format', type=click.Choice(['json', 'yaml']), default='json')
def convert(format):
    """Convert data between formats."""
    click.echo(f"Converting to {format} format")

def main():
    """Main entry point."""
    cli()

if __name__ == '__main__':
    main()
''')

        # Create pyproject.toml with entry points
        (tmpdir / "pyproject.toml").write_text('''
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "testcli"
version = "1.0.0"
description = "Test CLI project"
dependencies = [
    "click>=8.0.0",
]

[project.scripts]
testcli = "testcli.cli:main"
''')

        # Create config file
        (tmpdir / "config.yaml").write_text('''
app:
  name: testcli
  version: 1.0.0
  debug: false
''')

        # Create .env file
        (tmpdir / ".env.example").write_text('''
# Example environment variables
API_KEY=your_api_key_here
LOG_LEVEL=info
DEBUG=false
''')
