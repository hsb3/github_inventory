"""
Enhanced configuration file parsing for Python Quick Look tool.

This module provides comprehensive parsing of Python project configuration files
including pyproject.toml, setup.py, setup.cfg, requirements files, and various
tool configurations.
"""

import configparser
import logging
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)


@dataclass
class BuildSystemConfig:
    """Build system configuration information."""

    build_backend: Optional[str] = None
    requires: List[str] = field(default_factory=list)
    system: str = "unknown"  # setuptools, poetry, hatch, flit, etc.

    # Specific build system configurations
    setuptools_config: Dict[str, Any] = field(default_factory=dict)
    poetry_config: Dict[str, Any] = field(default_factory=dict)
    hatch_config: Dict[str, Any] = field(default_factory=dict)
    flit_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolConfig:
    """Configuration for development and analysis tools."""

    name: str
    config_source: str  # File where config was found
    settings: Dict[str, Any] = field(default_factory=dict)

    # Common tool settings extracted
    line_length: Optional[int] = None
    target_version: Optional[str] = None
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)


@dataclass
class DependencySpec:
    """Enhanced dependency specification."""

    name: str
    version_spec: Optional[str] = None
    markers: Optional[str] = None  # Environment markers like python_version>='3.8'
    extras: List[str] = field(default_factory=list)
    editable: bool = False
    url: Optional[str] = None  # For VCS or direct URL dependencies
    category: str = "main"  # main, dev, test, docs, etc.


@dataclass
class RequirementsFile:
    """Requirements file parsing results."""

    file_path: str
    dependencies: List[DependencySpec] = field(default_factory=list)
    constraints: List[DependencySpec] = field(default_factory=list)
    options: Dict[str, str] = field(default_factory=dict)  # pip options like --index-url
    includes: List[str] = field(default_factory=list)  # -r other-requirements.txt


@dataclass
class ProjectConfiguration:
    """Complete project configuration analysis."""

    # Build system
    build_system: Optional[BuildSystemConfig] = None

    # Dependencies from all sources
    dependencies: Dict[str, List[DependencySpec]] = field(default_factory=dict)

    # Requirements files
    requirements_files: List[RequirementsFile] = field(default_factory=list)

    # Tool configurations
    tool_configs: Dict[str, ToolConfig] = field(default_factory=dict)

    # Environment and deployment
    python_versions: Set[str] = field(default_factory=set)
    environment_variables: Set[str] = field(default_factory=set)

    # Configuration files found
    config_files: List[str] = field(default_factory=list)

    # Analysis metadata
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class PyProjectConfigAnalyzer:
    """Enhanced pyproject.toml configuration analyzer."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pyproject_path = project_root / "pyproject.toml"

    def analyze(self) -> Optional[Dict[str, Any]]:
        """Analyze pyproject.toml comprehensively."""
        if not self.pyproject_path.exists():
            return None

        try:
            with open(self.pyproject_path, "rb") as f:
                data = tomllib.load(f)

            return data
        except Exception as e:
            logger.warning(f"Error parsing pyproject.toml: {e}")
            return None

    def extract_build_system(self, data: Dict[str, Any]) -> Optional[BuildSystemConfig]:
        """Extract build system configuration."""
        build_system_data = data.get("build-system", {})
        if not build_system_data:
            return None

        config = BuildSystemConfig()
        config.build_backend = build_system_data.get("build-backend")
        config.requires = build_system_data.get("requires", [])

        # Determine build system type from backend
        if config.build_backend:
            if "setuptools" in config.build_backend:
                config.system = "setuptools"
            elif "poetry" in config.build_backend:
                config.system = "poetry"
            elif "hatch" in config.build_backend:
                config.system = "hatch"
            elif "flit" in config.build_backend:
                config.system = "flit"

        # Extract system-specific configurations
        if config.system == "poetry" and "tool" in data and "poetry" in data["tool"]:
            config.poetry_config = data["tool"]["poetry"]
        elif config.system == "hatch" and "tool" in data and "hatch" in data["tool"]:
            config.hatch_config = data["tool"]["hatch"]
        elif config.system == "flit" and "tool" in data and "flit" in data["tool"]:
            config.flit_config = data["tool"]["flit"]

        return config

    def extract_tool_configs(self, data: Dict[str, Any]) -> Dict[str, ToolConfig]:
        """Extract tool configurations from [tool.*] sections."""
        tools = {}
        tool_data = data.get("tool", {})

        for tool_name, tool_config in tool_data.items():
            if not isinstance(tool_config, dict):
                continue

            config = ToolConfig(
                name=tool_name,
                config_source="pyproject.toml",
                settings=tool_config
            )

            # Extract common settings
            self._extract_common_tool_settings(config, tool_config)

            tools[tool_name] = config

        return tools

    def _extract_common_tool_settings(self, config: ToolConfig, tool_config: Dict[str, Any]):
        """Extract common tool settings like line length, target version, etc."""
        # Line length (common for formatters and linters)
        if "line-length" in tool_config:
            config.line_length = tool_config["line-length"]
        elif "max-line-length" in tool_config:
            config.line_length = tool_config["max-line-length"]

        # Target version (for tools that support Python version targeting)
        if "target-version" in tool_config:
            if isinstance(tool_config["target-version"], list):
                config.target_version = ", ".join(tool_config["target-version"])
            else:
                config.target_version = str(tool_config["target-version"])

        # Include/exclude patterns
        if "include" in tool_config:
            patterns = tool_config["include"]
            if isinstance(patterns, str):
                config.include_patterns = [patterns]
            elif isinstance(patterns, list):
                config.include_patterns = patterns

        if "exclude" in tool_config:
            patterns = tool_config["exclude"]
            if isinstance(patterns, str):
                config.exclude_patterns = [patterns]
            elif isinstance(patterns, list):
                config.exclude_patterns = patterns

    def extract_dependencies(self, data: Dict[str, Any]) -> Dict[str, List[DependencySpec]]:
        """Extract all dependency information."""
        dependencies = {}

        # Main project dependencies
        project_data = data.get("project", {})
        if "dependencies" in project_data:
            dependencies["main"] = self._parse_dependency_specs(
                project_data["dependencies"], "main"
            )

        # Optional dependencies
        optional_deps = project_data.get("optional-dependencies", {})
        for group, deps in optional_deps.items():
            dependencies[group] = self._parse_dependency_specs(deps, group)

        # Poetry dependencies
        tool_data = data.get("tool", {})
        poetry_data = tool_data.get("poetry", {})
        if "dependencies" in poetry_data:
            poetry_main = self._parse_poetry_dependencies(
                poetry_data["dependencies"], "main"
            )
            if poetry_main:
                dependencies["main"] = dependencies.get("main", []) + poetry_main

        if "group" in poetry_data:
            for group, group_data in poetry_data["group"].items():
                if "dependencies" in group_data:
                    poetry_deps = self._parse_poetry_dependencies(
                        group_data["dependencies"], group
                    )
                    if poetry_deps:
                        dependencies[group] = poetry_deps

        return dependencies

    def _parse_dependency_specs(self, deps: List[str], category: str) -> List[DependencySpec]:
        """Parse PEP 508 dependency specifications."""
        dependencies = []

        for dep_str in deps:
            try:
                spec = self._parse_pep508_dependency(dep_str, category)
                if spec:
                    dependencies.append(spec)
            except Exception as e:
                logger.debug(f"Error parsing dependency '{dep_str}': {e}")

        return dependencies

    def _parse_pep508_dependency(self, dep_str: str, category: str) -> Optional[DependencySpec]:
        """Parse a single PEP 508 dependency specification."""
        # Basic PEP 508 parsing - this is simplified
        # Full implementation would use packaging library

        # Split on semicolon for markers
        parts = dep_str.split(";", 1)
        main_part = parts[0].strip()
        markers = parts[1].strip() if len(parts) > 1 else None

        # Extract name and version spec
        match = re.match(r"^([a-zA-Z0-9\-_.]+)(.*)$", main_part)
        if not match:
            return None

        name = match.group(1)
        version_part = match.group(2).strip()

        # Extract extras [extra1,extra2]
        extras = []
        extras_match = re.search(r"\[([^\]]+)\]", version_part)
        if extras_match:
            extras_str = extras_match.group(1)
            extras = [extra.strip() for extra in extras_str.split(",")]
            version_part = re.sub(r"\[([^\]]+)\]", "", version_part).strip()

        return DependencySpec(
            name=name,
            version_spec=version_part if version_part else None,
            markers=markers,
            extras=extras,
            category=category
        )

    def _parse_poetry_dependencies(self, deps: Dict[str, Any], category: str) -> List[DependencySpec]:
        """Parse Poetry-style dependency specifications."""
        dependencies = []

        for name, spec in deps.items():
            if name == "python":  # Skip Python version spec
                continue

            dep = DependencySpec(name=name, category=category)

            if isinstance(spec, str):
                dep.version_spec = spec
            elif isinstance(spec, dict):
                dep.version_spec = spec.get("version")
                dep.markers = spec.get("markers")
                dep.url = spec.get("url") or spec.get("git")
                dep.editable = spec.get("develop", False)

                # Extract extras
                if "extras" in spec:
                    dep.extras = spec["extras"]

            dependencies.append(dep)

        return dependencies


class SetupConfigAnalyzer:
    """Analyzer for setup.py and setup.cfg files."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.setup_py_path = project_root / "setup.py"
        self.setup_cfg_path = project_root / "setup.cfg"

    def analyze_setup_cfg(self) -> Optional[Dict[str, Any]]:
        """Analyze setup.cfg file."""
        if not self.setup_cfg_path.exists():
            return None

        try:
            config = configparser.ConfigParser()
            config.read(self.setup_cfg_path)

            # Convert to dictionary
            result = {}
            for section in config.sections():
                result[section] = dict(config[section])

            return result
        except Exception as e:
            logger.warning(f"Error parsing setup.cfg: {e}")
            return None

    def extract_tool_configs_from_setup_cfg(self, data: Dict[str, Any]) -> Dict[str, ToolConfig]:
        """Extract tool configurations from setup.cfg."""
        tools = {}

        for section_name, section_data in data.items():
            # Tool configurations often have section names like [tool:pytest] or [mypy]
            if section_name.startswith("tool:"):
                tool_name = section_name.replace("tool:", "")
            elif section_name in ["mypy", "flake8", "pytest", "coverage:run", "coverage:report"]:
                tool_name = section_name.split(":")[0]  # Handle coverage:run -> coverage
            else:
                continue

            config = ToolConfig(
                name=tool_name,
                config_source="setup.cfg",
                settings=section_data
            )

            # Extract common settings
            self._extract_common_settings_from_setup_cfg(config, section_data)

            tools[tool_name] = config

        return tools

    def _extract_common_settings_from_setup_cfg(self, config: ToolConfig, section_data: Dict[str, Any]):
        """Extract common settings from setup.cfg format."""
        # Line length
        if "max-line-length" in section_data:
            try:
                config.line_length = int(section_data["max-line-length"])
            except ValueError:
                pass

        # Include/exclude patterns (often comma-separated in setup.cfg)
        if "exclude" in section_data:
            exclude_str = section_data["exclude"]
            config.exclude_patterns = [p.strip() for p in exclude_str.split(",")]


class RequirementsAnalyzer:
    """Analyzer for requirements.txt and related files."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

        # Common requirements file patterns
        self.requirements_patterns = [
            "requirements.txt",
            "requirements-dev.txt",
            "requirements-test.txt",
            "requirements-docs.txt",
            "dev-requirements.txt",
            "test-requirements.txt",
            "constraints.txt",
            "requirements/*.txt"
        ]

    def find_requirements_files(self) -> List[Path]:
        """Find all requirements files in the project."""
        files = []

        for pattern in self.requirements_patterns:
            if "*" in pattern:
                # Use glob for patterns with wildcards
                matches = list(self.project_root.glob(pattern))
                files.extend(matches)
            else:
                # Direct file check
                file_path = self.project_root / pattern
                if file_path.exists():
                    files.append(file_path)

        return files

    def analyze_requirements_file(self, file_path: Path) -> RequirementsFile:
        """Analyze a single requirements file."""
        req_file = RequirementsFile(file_path=str(file_path.relative_to(self.project_root)))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Handle pip options and editable installs
                if line.startswith("-") and not line.startswith("-e "):
                    # Pip option (but not editable install)
                    self._parse_pip_option(line, req_file)
                else:
                    # Parse dependency (including -e editable installs)
                    dep = self._parse_requirements_dependency(line, req_file.file_path)
                    if dep:
                        req_file.dependencies.append(dep)

        except Exception as e:
            logger.warning(f"Error parsing requirements file {file_path}: {e}")

        return req_file

    def _parse_pip_option(self, line: str, req_file: RequirementsFile):
        """Parse pip options like -r, --index-url, etc."""
        parts = line.split(None, 1)
        if len(parts) < 2:
            return

        option, value = parts[0], parts[1]

        if option in ["-r", "--requirement"]:
            req_file.includes.append(value)
        elif option in ["--index-url", "--extra-index-url", "--find-links"]:
            req_file.options[option] = value

    def _parse_requirements_dependency(self, line: str, source_file: str) -> Optional[DependencySpec]:
        """Parse a dependency line from requirements file."""
        try:
            # Remove inline comments
            line = re.sub(r'\s+#.*$', '', line)

            # Handle editable installs
            editable = False
            if line.startswith("-e "):
                editable = True
                line = line[3:].strip()

            # Handle VCS URLs
            if any(vcs in line for vcs in ["git+", "hg+", "svn+", "bzr+"]):
                # VCS dependency
                if "#egg=" in line:
                    url_part, egg_part = line.split("#egg=", 1)
                    name = egg_part.split("[")[0]  # Remove extras from egg name
                    extras = []
                    if "[" in egg_part and "]" in egg_part:
                        extras_match = re.search(r'\[([^\]]+)\]', egg_part)
                        if extras_match:
                            extras = [e.strip() for e in extras_match.group(1).split(",")]

                    return DependencySpec(
                        name=name,
                        url=url_part,
                        editable=editable,
                        extras=extras,
                        category=self._infer_category_from_filename(source_file)
                    )
                else:
                    # VCS URL without egg name - try to infer name from URL
                    name = self._infer_name_from_url(line)
                    if name:
                        return DependencySpec(
                            name=name,
                            url=line,
                            editable=editable,
                            category=self._infer_category_from_filename(source_file)
                        )

            # Handle local editable installs (paths)
            if editable and (line.startswith("./") or line.startswith("../") or "/" in line):
                # Local editable dependency
                from pathlib import Path
                name = Path(line).name  # Use directory name as package name
                return DependencySpec(
                    name=name,
                    url=line,
                    editable=editable,
                    category=self._infer_category_from_filename(source_file)
                )

            # Regular dependency
            # Split on semicolon for markers
            parts = line.split(";", 1)
            main_part = parts[0].strip()
            markers = parts[1].strip() if len(parts) > 1 else None

            # Extract name and version spec
            match = re.match(r"^([a-zA-Z0-9\-_.]+)(.*)$", main_part)
            if not match:
                return None

            name = match.group(1)
            version_part = match.group(2).strip()

            # Extract extras
            extras = []
            extras_match = re.search(r"\[([^\]]+)\]", version_part)
            if extras_match:
                extras_str = extras_match.group(1)
                extras = [extra.strip() for extra in extras_str.split(",")]
                version_part = re.sub(r"\[([^\]]+)\]", "", version_part).strip()

            return DependencySpec(
                name=name,
                version_spec=version_part if version_part else None,
                markers=markers,
                extras=extras,
                editable=editable,
                category=self._infer_category_from_filename(source_file)
            )

        except Exception as e:
            logger.debug(f"Error parsing dependency line '{line}': {e}")
            return None

    def _infer_name_from_url(self, url: str) -> Optional[str]:
        """Infer package name from VCS URL."""
        try:
            # Extract repo name from various URL formats
            if ".git" in url:
                # Remove .git suffix and extract repo name
                repo_part = url.split(".git")[0]
                name = repo_part.split("/")[-1]
            elif "/" in url:
                name = url.split("/")[-1]
            else:
                return None

            # Clean up the name
            name = name.replace("-", "_").replace(".", "_")
            return name if name else None
        except Exception:
            return None

    def _infer_category_from_filename(self, filename: str) -> str:
        """Infer dependency category from filename."""
        filename_lower = filename.lower()

        if "dev" in filename_lower:
            return "dev"
        elif "test" in filename_lower:
            return "test"
        elif "doc" in filename_lower:
            return "docs"
        elif "constraint" in filename_lower:
            return "constraints"
        else:
            return "main"


class EnvironmentAnalyzer:
    """Analyzer for environment variables and deployment configuration."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def extract_environment_variables(self) -> Set[str]:
        """Extract environment variables from various sources."""
        env_vars = set()

        # Check common files for environment variables
        env_files = [
            ".env",
            ".env.example",
            ".env.template",
            "docker-compose.yml",
            "docker-compose.yaml",
            "Dockerfile",
            "tox.ini"
        ]

        for filename in env_files:
            file_path = self.project_root / filename
            if file_path.exists():
                env_vars.update(self._extract_env_vars_from_file(file_path))

        return env_vars

    def _extract_env_vars_from_file(self, file_path: Path) -> Set[str]:
        """Extract environment variables from a specific file."""
        env_vars = set()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Different patterns for different file types
            if file_path.name.startswith(".env"):
                # .env files: KEY=value
                for match in re.finditer(r'^([A-Z_][A-Z0-9_]*)\s*=', content, re.MULTILINE):
                    env_vars.add(match.group(1))

            elif file_path.name in ["docker-compose.yml", "docker-compose.yaml"]:
                # Docker compose files: environment variables
                for match in re.finditer(r'-\s+([A-Z_][A-Z0-9_]*)', content):
                    env_vars.add(match.group(1))
                # Also ${VAR} patterns
                for match in re.finditer(r'\${([A-Z_][A-Z0-9_]*)}', content):
                    env_vars.add(match.group(1))

            elif file_path.name == "Dockerfile":
                # Dockerfile ENV statements
                for match in re.finditer(r'ENV\s+([A-Z_][A-Z0-9_]*)', content):
                    env_vars.add(match.group(1))

            # General pattern: ${VAR} or $VAR references
            for match in re.finditer(r'\${([A-Z_][A-Z0-9_]*)}', content):
                env_vars.add(match.group(1))
            for match in re.finditer(r'\$([A-Z_][A-Z0-9_]*)', content):
                env_vars.add(match.group(1))

        except Exception as e:
            logger.debug(f"Error extracting environment variables from {file_path}: {e}")

        return env_vars


class ConfigurationAnalyzer:
    """Main configuration analyzer that coordinates all configuration analysis."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

        # Initialize sub-analyzers
        self.pyproject_analyzer = PyProjectConfigAnalyzer(project_root)
        self.setup_analyzer = SetupConfigAnalyzer(project_root)
        self.requirements_analyzer = RequirementsAnalyzer(project_root)
        self.environment_analyzer = EnvironmentAnalyzer(project_root)

    def analyze(self) -> ProjectConfiguration:
        """Perform comprehensive configuration analysis."""
        config = ProjectConfiguration()

        try:
            # Analyze pyproject.toml
            pyproject_data = self.pyproject_analyzer.analyze()
            if pyproject_data:
                config.config_files.append("pyproject.toml")

                # Build system
                config.build_system = self.pyproject_analyzer.extract_build_system(pyproject_data)

                # Tool configurations
                tool_configs = self.pyproject_analyzer.extract_tool_configs(pyproject_data)
                config.tool_configs.update(tool_configs)

                # Dependencies
                dependencies = self.pyproject_analyzer.extract_dependencies(pyproject_data)
                config.dependencies.update(dependencies)

                # Python version requirements
                project_data = pyproject_data.get("project", {})
                if "requires-python" in project_data:
                    config.python_versions.add(project_data["requires-python"])

            # Analyze setup.cfg
            setup_cfg_data = self.setup_analyzer.analyze_setup_cfg()
            if setup_cfg_data:
                config.config_files.append("setup.cfg")

                # Tool configurations from setup.cfg
                tool_configs = self.setup_analyzer.extract_tool_configs_from_setup_cfg(setup_cfg_data)
                config.tool_configs.update(tool_configs)

            # Analyze requirements files
            req_files = self.requirements_analyzer.find_requirements_files()
            for req_file_path in req_files:
                req_file = self.requirements_analyzer.analyze_requirements_file(req_file_path)
                config.requirements_files.append(req_file)
                config.config_files.append(str(req_file_path.relative_to(self.project_root)))

                # Add dependencies to main collection
                if req_file.dependencies:
                    category = self.requirements_analyzer._infer_category_from_filename(req_file.file_path)
                    if category not in config.dependencies:
                        config.dependencies[category] = []
                    config.dependencies[category].extend(req_file.dependencies)

            # Analyze environment variables
            config.environment_variables = self.environment_analyzer.extract_environment_variables()

            # Find additional config files
            additional_configs = [
                "tox.ini", "pytest.ini", ".coveragerc",
                ".pre-commit-config.yaml", ".github/workflows",
                "Makefile", "justfile"
            ]

            for config_file in additional_configs:
                file_path = self.project_root / config_file
                if file_path.exists():
                    config.config_files.append(config_file)

        except Exception as e:
            error_msg = f"Error during configuration analysis: {e}"
            logger.error(error_msg)
            config.errors.append(error_msg)

        return config

    def get_configuration_summary(self, config: ProjectConfiguration) -> Dict[str, Any]:
        """Generate a summary of configuration analysis."""
        summary = {
            "build_system": config.build_system.system if config.build_system else "unknown",
            "dependency_categories": list(config.dependencies.keys()),
            "total_dependencies": sum(len(deps) for deps in config.dependencies.values()),
            "tools_configured": list(config.tool_configs.keys()),
            "config_files_found": len(config.config_files),
            "environment_variables": len(config.environment_variables),
            "python_versions": list(config.python_versions),
            "has_errors": len(config.errors) > 0,
            "has_warnings": len(config.warnings) > 0
        }

        return summary
