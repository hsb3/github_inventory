#!/usr/bin/env python3
"""
Python Project Quick Look Tool

A comprehensive AST-based analyzer that provides detailed insights into Python project structure.
Similar to how pytest discovers tests, this tool uses static analysis to inventory all classes,
methods, and functions with their docstrings and signatures.
"""

import ast
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .project_context import ProjectContext, ProjectContextAnalyzer
    from .dependency_analyzer import DependencyAnalyzer, DependencyAnalysisResult
    from .cli_analyzer import CLIAnalyzer, CLIAnalysisResult
    from .configuration_analyzer import ConfigurationAnalyzer, ProjectConfiguration
    from .github_support import GitHubSupport, GitHubRepo
except ImportError:
    # Handle case where module is run directly
    from project_context import ProjectContext, ProjectContextAnalyzer
    from dependency_analyzer import DependencyAnalyzer, DependencyAnalysisResult
    from cli_analyzer import CLIAnalyzer, CLIAnalysisResult
    from configuration_analyzer import ConfigurationAnalyzer, ProjectConfiguration
    from github_support import GitHubSupport, GitHubRepo


@dataclass
class FunctionInfo:
    """Information about a function or method."""

    name: str
    signature: str
    docstring: Optional[str]
    decorators: List[str] = field(default_factory=list)
    lineno: int = 0
    is_async: bool = False
    is_method: bool = False
    is_property: bool = False
    is_staticmethod: bool = False
    is_classmethod: bool = False


@dataclass
class ClassInfo:
    """Information about a class."""

    name: str
    docstring: Optional[str]
    bases: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    lineno: int = 0


@dataclass
class ModuleInfo:
    """Information about a Python module."""

    name: str
    path: str
    docstring: Optional[str]
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)


class PythonQuickLook:
    """Main analyzer class for Python project structure.

    Supports both local directories and GitHub repositories.

    Examples:
        # Local directory
        analyzer = PythonQuickLook("/path/to/project")

        # GitHub repository
        analyzer = PythonQuickLook("github.com/user/repo")
        analyzer = PythonQuickLook("https://github.com/user/repo")
        analyzer = PythonQuickLook("user/repo")
    """

    def __init__(
        self, target: str = ".", ignore_patterns: Optional[List[str]] = None
    ):
        self.original_target = target
        self.ignore_patterns = ignore_patterns or [
            "__pycache__",
            ".git",
            ".pytest_cache",
            ".venv",
            "venv",
            "node_modules",
            ".tox",
            "build",
            "dist",
            "*.egg-info",
        ]
        self.modules: List[ModuleInfo] = []
        self.project_context: Optional[ProjectContext] = None
        self.dependency_analysis: Optional[DependencyAnalysisResult] = None
        self.cli_analysis: Optional[CLIAnalysisResult] = None
        self.configuration_analysis: Optional[ProjectConfiguration] = None

        # GitHub support
        self.github_support: Optional[GitHubSupport] = None
        self.github_repo: Optional[GitHubRepo] = None
        self.is_github_repo = False

        # Initialize target directory (local or GitHub)
        self._initialize_target(target)

    def _initialize_target(self, target: str):
        """Initialize the target directory, handling both local paths and GitHub URLs."""
        # Check if this looks like a GitHub URL
        github_support = GitHubSupport()
        github_repo = github_support.parse_github_url(target)

        if github_repo:
            # This is a GitHub repository
            self.is_github_repo = True
            self.github_support = github_support

            try:
                repo_info, local_path = github_support.analyze_github_url(target)
                if repo_info and local_path:
                    self.github_repo = repo_info
                    self.target_dir = local_path
                    print(f"📦 Cloned {repo_info.full_name} for analysis")
                else:
                    raise ValueError(f"Failed to clone GitHub repository: {target}")
            except Exception as e:
                raise ValueError(f"GitHub repository error: {e}")
        else:
            # This is a local directory
            self.is_github_repo = False
            self.target_dir = Path(target)

            if not self.target_dir.exists():
                raise ValueError(f"Directory does not exist: {target}")

    def should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored based on ignore patterns."""
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if pattern in path_str or path.name.startswith("."):
                return True
        return False

    def find_python_files(self) -> List[Path]:
        """Discover all Python files in the target directory."""
        python_files = []

        for root, dirs, files in os.walk(self.target_dir):
            root_path = Path(root)

            # Filter directories to ignore
            dirs[:] = [d for d in dirs if not self.should_ignore(root_path / d)]

            for file in files:
                if file.endswith(".py"):
                    file_path = root_path / file
                    if not self.should_ignore(file_path):
                        python_files.append(file_path)

        return sorted(python_files)

    def get_function_signature(self, node: ast.FunctionDef) -> str:
        """Extract function signature from AST node."""
        args = []

        # Regular arguments
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)

        # *args
        if node.args.vararg:
            vararg_str = f"*{node.args.vararg.arg}"
            if node.args.vararg.annotation:
                vararg_str += f": {ast.unparse(node.args.vararg.annotation)}"
            args.append(vararg_str)

        # **kwargs
        if node.args.kwarg:
            kwarg_str = f"**{node.args.kwarg.arg}"
            if node.args.kwarg.annotation:
                kwarg_str += f": {ast.unparse(node.args.kwarg.annotation)}"
            args.append(kwarg_str)

        # Return type
        return_annotation = ""
        if node.returns:
            return_annotation = f" -> {ast.unparse(node.returns)}"

        return f"{node.name}({', '.join(args)}){return_annotation}"

    def get_decorators(self, node) -> List[str]:
        """Extract decorator names from AST node."""
        decorators = []
        for decorator in node.decorator_list:
            try:
                decorators.append(ast.unparse(decorator))
            except Exception:
                decorators.append("<complex_decorator>")
        return decorators

    def analyze_function(
        self, node: ast.FunctionDef, is_method: bool = False
    ) -> FunctionInfo:
        """Analyze a function or method node."""
        docstring = ast.get_docstring(node)
        signature = self.get_function_signature(node)
        decorators = self.get_decorators(node)

        # Determine function type
        is_property = any("property" in dec for dec in decorators)
        is_staticmethod = any("staticmethod" in dec for dec in decorators)
        is_classmethod = any("classmethod" in dec for dec in decorators)
        is_async = isinstance(node, ast.AsyncFunctionDef)

        return FunctionInfo(
            name=node.name,
            signature=signature,
            docstring=docstring,
            decorators=decorators,
            lineno=node.lineno,
            is_async=is_async,
            is_method=is_method,
            is_property=is_property,
            is_staticmethod=is_staticmethod,
            is_classmethod=is_classmethod,
        )

    def analyze_class(self, node: ast.ClassDef) -> ClassInfo:
        """Analyze a class node."""
        docstring = ast.get_docstring(node)
        bases = [ast.unparse(base) for base in node.bases]
        decorators = self.get_decorators(node)

        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self.analyze_function(item, is_method=True)
                methods.append(method_info)

        return ClassInfo(
            name=node.name,
            docstring=docstring,
            bases=bases,
            methods=methods,
            decorators=decorators,
            lineno=node.lineno,
        )

    def analyze_module(self, file_path: Path) -> Optional[ModuleInfo]:
        """Analyze a single Python file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            module_docstring = ast.get_docstring(tree)

            # Determine module name
            rel_path = file_path.relative_to(self.target_dir)
            module_name = (
                str(rel_path).replace("/", ".").replace("\\", ".").replace(".py", "")
            )

            module_info = ModuleInfo(
                name=module_name, path=str(rel_path), docstring=module_docstring
            )

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_info.imports.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        module_info.imports.append(f"from {module} import {alias.name}")

            # Extract top-level classes and functions
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    class_info = self.analyze_class(node)
                    module_info.classes.append(class_info)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_info = self.analyze_function(node)
                    module_info.functions.append(func_info)

            return module_info

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
            return None

    def analyze_project(self) -> None:
        """Analyze the entire project."""
        python_files = self.find_python_files()
        print(f"Found {len(python_files)} Python files to analyze...")

        for file_path in python_files:
            module_info = self.analyze_module(file_path)
            if module_info:
                self.modules.append(module_info)

        # Analyze project context
        context_analyzer = ProjectContextAnalyzer(self.target_dir)
        self.project_context = context_analyzer.analyze(self.modules)

        # Analyze dependencies
        dependency_analyzer = DependencyAnalyzer(self.target_dir)
        self.dependency_analysis = dependency_analyzer.analyze(self.modules)

        # Analyze CLI patterns
        cli_analyzer = CLIAnalyzer(self.target_dir)
        self.cli_analysis = cli_analyzer.analyze(self.modules)

        # Analyze configuration files
        config_analyzer = ConfigurationAnalyzer(self.target_dir)
        self.configuration_analysis = config_analyzer.analyze()

    def cleanup(self):
        """Clean up resources, especially for GitHub repositories."""
        if self.is_github_repo and self.github_support:
            self.github_support.cleanup()
            print("🧹 Cleaned up temporary GitHub repository")

    def __del__(self):
        """Destructor to ensure cleanup happens."""
        try:
            self.cleanup()
        except:
            pass  # Ignore cleanup errors in destructor

    def get_statistics(self) -> Dict[str, int]:
        """Get summary statistics."""
        stats = {
            "modules": len(self.modules),
            "classes": sum(len(m.classes) for m in self.modules),
            "functions": sum(len(m.functions) for m in self.modules),
            "methods": sum(len(c.methods) for m in self.modules for c in m.classes),
            "documented_classes": sum(
                1 for m in self.modules for c in m.classes if c.docstring
            ),
            "documented_functions": sum(
                1 for m in self.modules for f in m.functions if f.docstring
            ),
            "documented_methods": sum(
                1
                for m in self.modules
                for c in m.classes
                for f in c.methods
                if f.docstring
            ),
        }
        return stats


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Python Project Quick Look Tool",
        epilog="Examples:\n"
               "  %(prog)s .                           # Analyze current directory\n"
               "  %(prog)s /path/to/project           # Analyze local directory\n"
               "  %(prog)s github.com/user/repo       # Analyze GitHub repository\n"
               "  %(prog)s https://github.com/user/repo # Analyze GitHub repository\n"
               "  %(prog)s user/repo                  # Analyze GitHub repository",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Target directory or GitHub repository URL to analyze",
    )
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--concise", action="store_true", help="Generate concise report")

    args = parser.parse_args()

    analyzer = None
    try:
        analyzer = PythonQuickLook(args.target)
        analyzer.analyze_project()

        if args.concise:
            # Generate concise report
            try:
                from .concise_report_generator import ConciseReportGenerator
            except ImportError:
                from concise_report_generator import ConciseReportGenerator

            generator = ConciseReportGenerator(analyzer)
            report = generator.generate()

            if args.output:
                with open(args.output, "w") as f:
                    f.write(report)
                print(f"📄 Concise report saved to: {args.output}")
            else:
                print(report)

        elif args.json:
            # JSON output implementation
            import json
            stats = analyzer.get_statistics()
            output = json.dumps(stats, indent=2)

            if args.output:
                with open(args.output, "w") as f:
                    f.write(output)
                print(f"📄 JSON stats saved to: {args.output}")
            else:
                print(output)
        else:
            # Generate full markdown report
            try:
                from .report_generator import MarkdownReportGenerator
            except ImportError:
                from report_generator import MarkdownReportGenerator

            generator = MarkdownReportGenerator(analyzer)
            report = generator.generate()

            if args.output:
                with open(args.output, "w") as f:
                    f.write(report)
                print(f"📄 Full report saved to: {args.output}")
            else:
                print(report)

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        # Always cleanup GitHub repositories
        if analyzer:
            analyzer.cleanup()


if __name__ == "__main__":
    main()
