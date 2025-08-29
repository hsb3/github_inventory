"""
Project context analysis module for Python Quick Look tool.

This module provides comprehensive analysis of Python project structure including
README parsing, pyproject.toml/setup.py analysis, CLI detection, and entry point
identification.
"""

import ast
import logging
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


@dataclass
class EntryPoint:
    """Information about a project entry point."""

    name: str
    module_path: str
    function_name: str
    description: Optional[str] = None
    entry_type: str = "console_script"  # console_script, gui_script, etc.


@dataclass
class CLICommand:
    """Information about a CLI command or subcommand."""

    name: str
    module_path: str
    function_name: str
    arguments: List[str] = field(default_factory=list)
    options: List[str] = field(default_factory=list)
    description: Optional[str] = None
    parent_command: Optional[str] = None


@dataclass
class ProjectDependency:
    """Information about a project dependency."""

    name: str
    version_spec: Optional[str] = None
    is_optional: bool = False
    group: str = "main"  # main, dev, optional, etc.
    extras: List[str] = field(default_factory=list)


@dataclass
class ProjectMetadata:
    """Project metadata from pyproject.toml or setup.py."""

    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    author_email: Optional[str] = None
    license: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    classifiers: List[str] = field(default_factory=list)
    python_requires: Optional[str] = None
    dependencies: List[ProjectDependency] = field(default_factory=list)
    optional_dependencies: Dict[str, List[ProjectDependency]] = field(default_factory=dict)
    entry_points: List[EntryPoint] = field(default_factory=list)


@dataclass
class READMEInfo:
    """Information extracted from README files."""

    file_path: str
    title: Optional[str] = None
    description: Optional[str] = None
    installation_section: Optional[str] = None
    usage_section: Optional[str] = None
    badges: List[str] = field(default_factory=list)
    links: List[Tuple[str, str]] = field(default_factory=list)  # (text, url)
    has_toc: bool = False
    sections: List[str] = field(default_factory=list)


@dataclass
class ProjectStructure:
    """Information about project directory structure."""

    is_package: bool = False
    has_src_layout: bool = False
    package_dirs: List[str] = field(default_factory=list)
    test_dirs: List[str] = field(default_factory=list)
    doc_dirs: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    has_dockerfile: bool = False
    has_docker_compose: bool = False
    has_makefile: bool = False
    has_requirements_txt: bool = False
    has_poetry_lock: bool = False
    has_pipfile: bool = False


@dataclass
class ProjectContext:
    """Complete project context information."""

    root_path: str
    project_name: str
    metadata: Optional[ProjectMetadata] = None
    readme_info: Optional[READMEInfo] = None
    structure: Optional[ProjectStructure] = None
    cli_commands: List[CLICommand] = field(default_factory=list)
    detected_frameworks: List[str] = field(default_factory=list)
    detected_patterns: List[str] = field(default_factory=list)


class PyProjectAnalyzer:
    """Analyzes pyproject.toml files."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pyproject_path = project_root / "pyproject.toml"

    def analyze(self) -> Optional[ProjectMetadata]:
        """Analyze pyproject.toml file."""
        if not self.pyproject_path.exists():
            return None

        try:
            with open(self.pyproject_path, "rb") as f:
                data = tomllib.load(f)

            project_data = data.get("project", {})
            metadata = ProjectMetadata()

            # Basic metadata
            metadata.name = project_data.get("name")
            metadata.version = project_data.get("version")
            metadata.description = project_data.get("description")
            metadata.license = self._extract_license(project_data.get("license"))
            metadata.python_requires = project_data.get("requires-python")
            metadata.keywords = project_data.get("keywords", [])
            metadata.classifiers = project_data.get("classifiers", [])

            # Authors
            authors = project_data.get("authors", [])
            if authors:
                author = authors[0]
                metadata.author = author.get("name")
                metadata.author_email = author.get("email")

            # URLs
            urls = project_data.get("urls", {})
            metadata.homepage = urls.get("Homepage") or urls.get("homepage")
            metadata.repository = urls.get("Repository") or urls.get("repository")

            # Dependencies
            deps = project_data.get("dependencies", [])
            metadata.dependencies = self._parse_dependencies(deps, "main")

            # Optional dependencies
            optional_deps = project_data.get("optional-dependencies", {})
            for group, deps in optional_deps.items():
                metadata.optional_dependencies[group] = self._parse_dependencies(deps, group)

            # Entry points (scripts)
            scripts = project_data.get("scripts", {})
            for name, entry in scripts.items():
                module_path, func_name = self._parse_entry_point(entry)
                metadata.entry_points.append(EntryPoint(
                    name=name,
                    module_path=module_path,
                    function_name=func_name,
                    entry_type="console_script"
                ))

            # GUI scripts
            gui_scripts = project_data.get("gui-scripts", {})
            for name, entry in gui_scripts.items():
                module_path, func_name = self._parse_entry_point(entry)
                metadata.entry_points.append(EntryPoint(
                    name=name,
                    module_path=module_path,
                    function_name=func_name,
                    entry_type="gui_script"
                ))

            return metadata

        except Exception as e:
            logger.warning(f"Error parsing pyproject.toml: {e}")
            return None

    def _extract_license(self, license_data: Union[str, Dict, None]) -> Optional[str]:
        """Extract license information."""
        if isinstance(license_data, str):
            return license_data
        elif isinstance(license_data, dict):
            return license_data.get("text") or license_data.get("file")
        return None

    def _parse_dependencies(self, deps: List[str], group: str) -> List[ProjectDependency]:
        """Parse dependency strings into ProjectDependency objects."""
        dependencies = []
        for dep_str in deps:
            # Parse dependency string (e.g., "requests>=2.0.0", "pytest; python_version>='3.8'")
            # This is a simplified parser - a real implementation might use packaging library
            parts = dep_str.split(";")[0].strip()  # Remove conditions for now

            # Extract name and version spec
            name_match = re.match(r"^([a-zA-Z0-9\-_\.]+)", parts)
            if name_match:
                name = name_match.group(1)
                version_spec = parts[len(name):].strip() if len(parts) > len(name) else None

                dependencies.append(ProjectDependency(
                    name=name,
                    version_spec=version_spec,
                    group=group
                ))

        return dependencies

    def _parse_entry_point(self, entry: str) -> Tuple[str, str]:
        """Parse entry point string into module and function."""
        if ":" in entry:
            module_path, func_name = entry.split(":", 1)
            return module_path.strip(), func_name.strip()
        else:
            return entry.strip(), "main"


class SetupPyAnalyzer:
    """Analyzes setup.py files using safe AST parsing."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.setup_path = project_root / "setup.py"

    def analyze(self) -> Optional[ProjectMetadata]:
        """Analyze setup.py file using AST (no code execution)."""
        if not self.setup_path.exists():
            return None

        try:
            with open(self.setup_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            metadata = ProjectMetadata()

            # Find setup() call
            setup_call = self._find_setup_call(tree)
            if setup_call:
                self._extract_setup_args(setup_call, metadata)

            return metadata

        except Exception as e:
            logger.warning(f"Error parsing setup.py: {e}")
            return None

    def _find_setup_call(self, tree: ast.AST) -> Optional[ast.Call]:
        """Find the setup() function call."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "setup":
                    return node
                elif (isinstance(node.func, ast.Attribute) and
                      node.func.attr == "setup"):
                    return node
        return None

    def _extract_setup_args(self, call: ast.Call, metadata: ProjectMetadata) -> None:
        """Extract arguments from setup() call."""
        # Extract keyword arguments
        for keyword in call.keywords:
            if keyword.arg == "name":
                metadata.name = self._extract_string_value(keyword.value)
            elif keyword.arg == "version":
                metadata.version = self._extract_string_value(keyword.value)
            elif keyword.arg == "description":
                metadata.description = self._extract_string_value(keyword.value)
            elif keyword.arg == "author":
                metadata.author = self._extract_string_value(keyword.value)
            elif keyword.arg == "author_email":
                metadata.author_email = self._extract_string_value(keyword.value)
            elif keyword.arg == "url":
                metadata.homepage = self._extract_string_value(keyword.value)
            elif keyword.arg == "python_requires":
                metadata.python_requires = self._extract_string_value(keyword.value)
            elif keyword.arg == "install_requires":
                deps = self._extract_list_values(keyword.value)
                metadata.dependencies = [
                    ProjectDependency(name=dep, group="main") for dep in deps
                ]
            elif keyword.arg == "entry_points":
                self._extract_entry_points(keyword.value, metadata)

    def _extract_string_value(self, node: ast.AST) -> Optional[str]:
        """Extract string value from AST node."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        elif isinstance(node, ast.Str):  # Python < 3.8 compatibility
            return node.s
        return None

    def _extract_list_values(self, node: ast.AST) -> List[str]:
        """Extract list of string values from AST node."""
        values = []
        if isinstance(node, ast.List):
            for elem in node.elts:
                value = self._extract_string_value(elem)
                if value:
                    values.append(value)
        return values

    def _extract_entry_points(self, node: ast.AST, metadata: ProjectMetadata) -> None:
        """Extract entry points from AST node."""
        # This is a simplified implementation
        # Real entry points can be quite complex
        pass


class READMEAnalyzer:
    """Analyzes README files."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.readme_files = [
            "README.md", "README.rst", "README.txt", "README",
            "readme.md", "readme.rst", "readme.txt", "readme"
        ]

    def analyze(self) -> Optional[READMEInfo]:
        """Analyze README file."""
        readme_path = self._find_readme()
        if not readme_path:
            return None

        try:
            with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            info = READMEInfo(file_path=str(readme_path.relative_to(self.project_root)))

            if readme_path.suffix.lower() == ".md":
                self._analyze_markdown(content, info)
            elif readme_path.suffix.lower() == ".rst":
                self._analyze_rst(content, info)
            else:
                self._analyze_plain_text(content, info)

            return info

        except Exception as e:
            logger.warning(f"Error analyzing README: {e}")
            return None

    def _find_readme(self) -> Optional[Path]:
        """Find README file in project root."""
        for filename in self.readme_files:
            path = self.project_root / filename
            if path.exists():
                return path
        return None

    def _analyze_markdown(self, content: str, info: READMEInfo) -> None:
        """Analyze Markdown README."""
        lines = content.split("\n")

        # Extract title (first H1)
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                info.title = line[2:].strip()
                break

        # Extract sections
        current_section = None
        section_content = []

        for line in lines:
            line_stripped = line.strip()

            # Check for headers
            if line_stripped.startswith("#"):
                if current_section:
                    self._process_section(current_section, "\n".join(section_content), info)

                # Determine header level
                level = 0
                for char in line_stripped:
                    if char == "#":
                        level += 1
                    else:
                        break

                current_section = line_stripped[level:].strip().lower()
                section_content = []
                info.sections.append(current_section)
            else:
                section_content.append(line)

            # Extract badges
            if "![" in line or "[![" in line:
                badge_matches = re.findall(r"!\[.*?\]\(.*?\)", line)
                info.badges.extend(badge_matches)

            # Extract links
            link_matches = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", line)
            info.links.extend(link_matches)

        # Process last section
        if current_section:
            self._process_section(current_section, "\n".join(section_content), info)

        # Check for table of contents
        content_lower = content.lower()
        info.has_toc = any(toc in content_lower for toc in [
            "table of contents", "contents", "toc", "## contents"
        ])

    def _analyze_rst(self, content: str, info: READMEInfo) -> None:
        """Analyze reStructuredText README."""
        lines = content.split("\n")

        # Extract title (look for title with underline)
        for i, line in enumerate(lines):
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if len(next_line.strip()) > 0 and all(c in "=-~" for c in next_line.strip()):
                    info.title = line.strip()
                    break

        # Basic section extraction for RST
        for line in lines:
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith(" "):
                info.sections.append(line_stripped)

    def _analyze_plain_text(self, content: str, info: READMEInfo) -> None:
        """Analyze plain text README."""
        lines = content.split("\n")

        # Use first non-empty line as title
        for line in lines:
            line_stripped = line.strip()
            if line_stripped:
                info.title = line_stripped
                break

        # Extract description (first paragraph)
        description_lines = []
        found_content = False

        for line in lines[1:]:  # Skip title line
            line_stripped = line.strip()

            if not found_content and not line_stripped:
                continue

            if not line_stripped:
                if description_lines:
                    break
            else:
                found_content = True
                description_lines.append(line_stripped)

        if description_lines:
            info.description = " ".join(description_lines)

    def _process_section(self, section: str, content: str, info: READMEInfo) -> None:
        """Process a specific section of the README."""
        section_lower = section.lower()

        if any(keyword in section_lower for keyword in ["install", "setup", "getting started"]):
            info.installation_section = content.strip()
        elif any(keyword in section_lower for keyword in ["usage", "example", "quick start", "how to"]):
            info.usage_section = content.strip()
        elif not info.description and any(keyword in section_lower for keyword in ["description", "about", "overview"]):
            info.description = content.strip()


class ProjectStructureAnalyzer:
    """Analyzes project directory structure."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def analyze(self) -> ProjectStructure:
        """Analyze project structure."""
        structure = ProjectStructure()

        # Check for package structure
        structure.has_src_layout = (self.project_root / "src").is_dir()

        # Find package directories
        if structure.has_src_layout:
            src_dir = self.project_root / "src"
            structure.package_dirs = [
                str(d.relative_to(self.project_root))
                for d in src_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
        else:
            # Look for directories with __init__.py
            for item in self.project_root.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    if (item / "__init__.py").exists():
                        structure.package_dirs.append(str(item.relative_to(self.project_root)))

        structure.is_package = len(structure.package_dirs) > 0

        # Find test directories
        test_patterns = ["test", "tests", "test_", "tests_"]
        for item in self.project_root.rglob("*"):
            if item.is_dir():
                if any(pattern in item.name.lower() for pattern in test_patterns):
                    structure.test_dirs.append(str(item.relative_to(self.project_root)))

        # Find documentation directories
        doc_patterns = ["doc", "docs", "documentation"]
        for item in self.project_root.iterdir():
            if item.is_dir() and item.name.lower() in doc_patterns:
                structure.doc_dirs.append(str(item.relative_to(self.project_root)))

        # Check for common config files
        config_files = [
            "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
            "Pipfile", "poetry.lock", "Makefile", "Dockerfile",
            "docker-compose.yml", "docker-compose.yaml", ".gitignore",
            "tox.ini", "pytest.ini", ".pre-commit-config.yaml"
        ]

        for config_file in config_files:
            if (self.project_root / config_file).exists():
                structure.config_files.append(config_file)

        # Set specific flags
        structure.has_dockerfile = "Dockerfile" in structure.config_files
        structure.has_docker_compose = any(
            f in structure.config_files
            for f in ["docker-compose.yml", "docker-compose.yaml"]
        )
        structure.has_makefile = "Makefile" in structure.config_files
        structure.has_requirements_txt = "requirements.txt" in structure.config_files
        structure.has_poetry_lock = "poetry.lock" in structure.config_files
        structure.has_pipfile = "Pipfile" in structure.config_files

        return structure


class CLIDetector:
    """Detects CLI commands and interfaces."""

    def __init__(self, project_root: Path, modules: List):
        self.project_root = project_root
        self.modules = modules

    def detect_cli_commands(self) -> List[CLICommand]:
        """Detect CLI commands in the project."""
        commands = []

        # Look for argparse usage only in main or cli modules
        for module in self.modules:
            # Only analyze potential CLI modules
            if not self._is_potential_cli_module(module):
                continue

            try:
                module_path = self.project_root / module.path
                with open(module_path, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)
                commands.extend(self._analyze_argparse(tree, module.name))
                commands.extend(self._analyze_click(tree, module.name))
                commands.extend(self._analyze_typer(tree, module.name))

            except Exception as e:
                logger.debug(f"Error analyzing module {module.name} for CLI: {e}")

        return commands

    def _is_potential_cli_module(self, module) -> bool:
        """Check if module is likely to contain CLI commands."""
        module_name = module.name.lower()

        # Check for common CLI module names
        cli_indicators = [
            "main", "cli", "command", "cmd", "__main__",
            "run", "start", "script", "tool", "app"
        ]

        # Check if module name contains CLI indicators
        if any(indicator in module_name for indicator in cli_indicators):
            return True

        # Check if module has main function
        for func in module.functions:
            if func.name == "main":
                return True

        return False

    def _analyze_argparse(self, tree: ast.AST, module_name: str) -> List[CLICommand]:
        """Analyze argparse usage."""
        commands = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Look for ArgumentParser instantiation
                if (isinstance(node.func, ast.Attribute) and
                    node.func.attr == "ArgumentParser"):

                    # Extract description from arguments
                    description = None
                    for keyword in node.keywords:
                        if keyword.arg == "description":
                            description = self._extract_string_value(keyword.value)

                    commands.append(CLICommand(
                        name="main",
                        module_path=module_name,
                        function_name="main",
                        description=description
                    ))

        return commands

    def _analyze_click(self, tree: ast.AST, module_name: str) -> List[CLICommand]:
        """Analyze Click framework usage."""
        commands = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Look for @click.command decorator
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if (isinstance(decorator.func, ast.Attribute) and
                            decorator.func.attr == "command" and
                            isinstance(decorator.func.value, ast.Name) and
                            decorator.func.value.id == "click"):

                            commands.append(CLICommand(
                                name=node.name,
                                module_path=module_name,
                                function_name=node.name,
                                description=ast.get_docstring(node)
                            ))

        return commands

    def _analyze_typer(self, tree: ast.AST, module_name: str) -> List[CLICommand]:
        """Analyze Typer framework usage."""
        commands = []

        # Look for Typer app creation and command decorators
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function has type hints that suggest it's a Typer command
                if node.args.args:
                    # Typer commands often have typed arguments
                    has_annotations = any(arg.annotation for arg in node.args.args)
                    if has_annotations:
                        commands.append(CLICommand(
                            name=node.name,
                            module_path=module_name,
                            function_name=node.name,
                            description=ast.get_docstring(node)
                        ))

        return commands

    def _extract_string_value(self, node: ast.AST) -> Optional[str]:
        """Extract string value from AST node."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        elif isinstance(node, ast.Str):  # Python < 3.8 compatibility
            return node.s
        return None


class FrameworkDetector:
    """Detects common Python frameworks and patterns."""

    def __init__(self, project_root: Path, modules: List, dependencies: List[ProjectDependency]):
        self.project_root = project_root
        self.modules = modules
        self.dependencies = dependencies

    def detect_frameworks(self) -> Tuple[List[str], List[str]]:
        """Detect frameworks and patterns."""
        frameworks = set()
        patterns = set()

        # Detect from dependencies
        dep_names = [dep.name.lower() for dep in self.dependencies]

        # Web frameworks
        web_frameworks = {
            "flask": "Flask",
            "django": "Django",
            "fastapi": "FastAPI",
            "tornado": "Tornado",
            "pyramid": "Pyramid",
            "bottle": "Bottle",
            "cherrypy": "CherryPy",
            "starlette": "Starlette",
            "quart": "Quart"
        }

        for dep_name, framework_name in web_frameworks.items():
            if dep_name in dep_names:
                frameworks.add(framework_name)

        # CLI frameworks
        cli_frameworks = {
            "click": "Click",
            "typer": "Typer",
            "argparse": "argparse",
            "fire": "Python Fire",
            "cement": "Cement"
        }

        for dep_name, framework_name in cli_frameworks.items():
            if dep_name in dep_names:
                frameworks.add(framework_name)

        # Testing frameworks
        test_frameworks = {
            "pytest": "pytest",
            "unittest": "unittest",
            "nose": "nose",
            "nose2": "nose2"
        }

        for dep_name, framework_name in test_frameworks.items():
            if dep_name in dep_names:
                frameworks.add(framework_name)

        # Data science frameworks
        ds_frameworks = {
            "pandas": "Pandas",
            "numpy": "NumPy",
            "scipy": "SciPy",
            "matplotlib": "Matplotlib",
            "seaborn": "Seaborn",
            "plotly": "Plotly",
            "bokeh": "Bokeh",
            "streamlit": "Streamlit",
            "dash": "Dash",
            "jupyter": "Jupyter"
        }

        for dep_name, framework_name in ds_frameworks.items():
            if dep_name in dep_names:
                frameworks.add(framework_name)

        # Detect patterns from code structure
        if any("test" in module.name for module in self.modules):
            patterns.add("Testing")

        if any("cli" in module.name or "command" in module.name for module in self.modules):
            patterns.add("Command Line Interface")

        if any("api" in module.name for module in self.modules):
            patterns.add("API")

        if any("model" in module.name for module in self.modules):
            patterns.add("Data Modeling")

        if (self.project_root / "requirements.txt").exists():
            patterns.add("pip requirements")

        if (self.project_root / "Dockerfile").exists():
            patterns.add("Docker")

        if (self.project_root / "docker-compose.yml").exists() or (self.project_root / "docker-compose.yaml").exists():
            patterns.add("Docker Compose")

        return list(frameworks), list(patterns)


class ProjectContextAnalyzer:
    """Main analyzer that coordinates all project context analysis."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.project_name = project_root.name

    def analyze(self, modules: List = None) -> ProjectContext:
        """Perform comprehensive project context analysis."""
        modules = modules or []

        context = ProjectContext(
            root_path=str(self.project_root),
            project_name=self.project_name
        )

        # Analyze project metadata
        pyproject_analyzer = PyProjectAnalyzer(self.project_root)
        context.metadata = pyproject_analyzer.analyze()

        # If no pyproject.toml, try setup.py
        if not context.metadata:
            setup_analyzer = SetupPyAnalyzer(self.project_root)
            context.metadata = setup_analyzer.analyze()

        # Analyze README
        readme_analyzer = READMEAnalyzer(self.project_root)
        context.readme_info = readme_analyzer.analyze()

        # Analyze project structure
        structure_analyzer = ProjectStructureAnalyzer(self.project_root)
        context.structure = structure_analyzer.analyze()

        # Detect CLI commands
        if modules:
            cli_detector = CLIDetector(self.project_root, modules)
            context.cli_commands = cli_detector.detect_cli_commands()

        # Always detect frameworks and patterns (they can work without modules)
        dependencies = context.metadata.dependencies if context.metadata else []
        framework_detector = FrameworkDetector(self.project_root, modules or [], dependencies)
        frameworks, patterns = framework_detector.detect_frameworks()
        context.detected_frameworks = frameworks
        context.detected_patterns = patterns

        return context
