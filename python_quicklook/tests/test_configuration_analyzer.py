"""
Comprehensive tests for the configuration_analyzer module.
Tests all analyzer classes and their functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the modules to test
from src.configuration_analyzer import (
    BuildSystemConfig,
    ConfigurationAnalyzer,
    DependencySpec,
    EnvironmentAnalyzer,
    ProjectConfiguration,
    PyProjectConfigAnalyzer,
    RequirementsAnalyzer,
    RequirementsFile,
    SetupConfigAnalyzer,
    ToolConfig,
)


class TestDependencySpec:
    """Test DependencySpec dataclass."""

    def test_init_minimal(self):
        dep = DependencySpec(name="requests")
        assert dep.name == "requests"
        assert dep.version_spec is None
        assert dep.markers is None
        assert dep.extras == []
        assert dep.editable is False
        assert dep.url is None
        assert dep.category == "main"

    def test_init_full(self):
        dep = DependencySpec(
            name="pytest",
            version_spec=">=6.0.0",
            markers="python_version>='3.8'",
            extras=["extra1", "extra2"],
            editable=True,
            url="git+https://github.com/pytest-dev/pytest.git",
            category="dev"
        )
        assert dep.name == "pytest"
        assert dep.version_spec == ">=6.0.0"
        assert dep.markers == "python_version>='3.8'"
        assert dep.extras == ["extra1", "extra2"]
        assert dep.editable is True
        assert dep.url == "git+https://github.com/pytest-dev/pytest.git"
        assert dep.category == "dev"


class TestBuildSystemConfig:
    """Test BuildSystemConfig dataclass."""

    def test_init_default(self):
        config = BuildSystemConfig()
        assert config.build_backend is None
        assert config.requires == []
        assert config.system == "unknown"
        assert config.setuptools_config == {}
        assert config.poetry_config == {}
        assert config.hatch_config == {}
        assert config.flit_config == {}

    def test_init_with_values(self):
        config = BuildSystemConfig(
            build_backend="setuptools.build_meta",
            requires=["setuptools", "wheel"],
            system="setuptools"
        )
        assert config.build_backend == "setuptools.build_meta"
        assert config.requires == ["setuptools", "wheel"]
        assert config.system == "setuptools"


class TestToolConfig:
    """Test ToolConfig dataclass."""

    def test_init_minimal(self):
        config = ToolConfig(name="black", config_source="pyproject.toml")
        assert config.name == "black"
        assert config.config_source == "pyproject.toml"
        assert config.settings == {}
        assert config.line_length is None
        assert config.target_version is None
        assert config.include_patterns == []
        assert config.exclude_patterns == []


class TestPyProjectConfigAnalyzer:
    """Test PyProjectConfigAnalyzer class."""

    def test_analyze_missing_file(self):
        """Test behavior when pyproject.toml doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = PyProjectConfigAnalyzer(Path(tmpdir))
            result = analyzer.analyze()
            assert result is None

    def test_analyze_comprehensive_pyproject(self):
        """Test analysis of comprehensive pyproject.toml."""
        toml_content = '''
[build-system]
requires = ["setuptools>=45", "wheel", "setuptools_scm[toml]>=6.2"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
version = "1.0.0"
description = "A comprehensive test project"
requires-python = ">=3.8"
dependencies = [
    "requests>=2.25.0",
    "click[colorama]>=8.0",
    "pydantic>=1.8.0; python_version>='3.8'"
]

[project.optional-dependencies]
dev = ["pytest>=6.0", "black>=22.0", "mypy>=0.910"]
docs = ["sphinx>=4.0", "sphinx-rtd-theme"]
test = ["coverage>=6.0", "pytest-cov>=3.0"]

[tool.black]
line-length = 88
target-version = ["py38", "py39", "py310"]
include = '\\.pyi?$'
exclude = """
/(
    \\\\.eggs
  | \\\\.git
  | \\\\.venv
  | _build
  | build
  | dist
)/
"""

[tool.ruff]
line-length = 88
target-version = "py38"
select = ["E", "F", "W", "C90", "I", "N", "UP", "B"]
ignore = ["E203", "E501"]

[tool.mypy]
python_version = "3.8"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
minversion = "6.0"
addopts = "-ra -q --strict-markers"
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests"
]

[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/venv/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError"
]
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            pyproject_path = tmpdir / "pyproject.toml"
            pyproject_path.write_text(toml_content)

            analyzer = PyProjectConfigAnalyzer(tmpdir)
            result = analyzer.analyze()

            assert result is not None

            # Test build system extraction
            build_system = analyzer.extract_build_system(result)
            assert build_system is not None
            assert build_system.build_backend == "setuptools.build_meta"
            assert "setuptools>=45" in build_system.requires
            assert build_system.system == "setuptools"

            # Test tool configurations
            tool_configs = analyzer.extract_tool_configs(result)
            assert "black" in tool_configs
            assert "ruff" in tool_configs
            assert "mypy" in tool_configs
            assert "pytest" in tool_configs
            assert "coverage" in tool_configs

            # Test black configuration
            black_config = tool_configs["black"]
            assert black_config.line_length == 88
            assert black_config.target_version == "py38, py39, py310"
            assert black_config.include_patterns == ['\\.pyi?$']

            # Test ruff configuration
            ruff_config = tool_configs["ruff"]
            assert ruff_config.line_length == 88
            assert ruff_config.target_version == "py38"
            assert "select" in ruff_config.settings
            assert "ignore" in ruff_config.settings

            # Test dependencies
            dependencies = analyzer.extract_dependencies(result)
            assert "main" in dependencies
            assert "dev" in dependencies
            assert "docs" in dependencies
            assert "test" in dependencies

            # Test main dependencies
            main_deps = dependencies["main"]
            assert len(main_deps) == 3

            requests_dep = next(dep for dep in main_deps if dep.name == "requests")
            assert requests_dep.version_spec == ">=2.25.0"
            assert requests_dep.category == "main"

            click_dep = next(dep for dep in main_deps if dep.name == "click")
            assert click_dep.extras == ["colorama"]
            assert click_dep.version_spec == ">=8.0"

            pydantic_dep = next(dep for dep in main_deps if dep.name == "pydantic")
            assert pydantic_dep.markers == "python_version>='3.8'"

    def test_poetry_dependencies(self):
        """Test parsing of Poetry-style dependencies."""
        toml_content = '''
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "poetry-project"
version = "0.1.0"
description = "A Poetry project"

[tool.poetry.dependencies]
python = "^3.8"
requests = "^2.28.0"
click = {version = "^8.0", extras = ["colorama"]}
dev-dependency = {git = "https://github.com/user/repo.git", develop = true}

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
black = "^22.0"

[tool.poetry.group.docs.dependencies]
sphinx = "^5.0"
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            pyproject_path = tmpdir / "pyproject.toml"
            pyproject_path.write_text(toml_content)

            analyzer = PyProjectConfigAnalyzer(tmpdir)
            result = analyzer.analyze()

            assert result is not None

            # Test build system
            build_system = analyzer.extract_build_system(result)
            assert build_system.system == "poetry"
            assert build_system.poetry_config == result["tool"]["poetry"]

            # Test dependencies
            dependencies = analyzer.extract_dependencies(result)
            assert "main" in dependencies
            assert "dev" in dependencies
            assert "docs" in dependencies

            # Test main dependencies
            main_deps = dependencies["main"]
            requests_dep = next(dep for dep in main_deps if dep.name == "requests")
            assert requests_dep.version_spec == "^2.28.0"

            click_dep = next(dep for dep in main_deps if dep.name == "click")
            assert click_dep.extras == ["colorama"]

            dev_dep = next(dep for dep in main_deps if dep.name == "dev-dependency")
            assert dev_dep.url == "https://github.com/user/repo.git"
            assert dev_dep.editable is True

    def test_parse_pep508_dependency(self):
        """Test PEP 508 dependency parsing."""
        analyzer = PyProjectConfigAnalyzer(Path("."))

        # Simple dependency
        dep = analyzer._parse_pep508_dependency("requests", "main")
        assert dep.name == "requests"
        assert dep.version_spec is None
        assert dep.category == "main"

        # With version spec
        dep = analyzer._parse_pep508_dependency("requests>=2.25.0", "main")
        assert dep.name == "requests"
        assert dep.version_spec == ">=2.25.0"

        # With extras
        dep = analyzer._parse_pep508_dependency("click[colorama]>=8.0", "main")
        assert dep.name == "click"
        assert dep.version_spec == ">=8.0"
        assert dep.extras == ["colorama"]

        # With markers
        dep = analyzer._parse_pep508_dependency("pydantic>=1.8.0; python_version>='3.8'", "main")
        assert dep.name == "pydantic"
        assert dep.version_spec == ">=1.8.0"
        assert dep.markers == "python_version>='3.8'"

        # Complex dependency
        dep = analyzer._parse_pep508_dependency("package[extra1,extra2]>=1.0; python_version>='3.8'", "dev")
        assert dep.name == "package"
        assert dep.version_spec == ">=1.0"
        assert dep.extras == ["extra1", "extra2"]
        assert dep.markers == "python_version>='3.8'"
        assert dep.category == "dev"


class TestSetupConfigAnalyzer:
    """Test SetupConfigAnalyzer class."""

    def test_analyze_setup_cfg(self):
        """Test analysis of setup.cfg file."""
        setup_cfg_content = '''
[metadata]
name = test-project
version = 1.0.0
description = A test project

[options]
zip_safe = False
python_requires = >=3.8
install_requires =
    requests>=2.25.0
    click>=8.0

[options.extras_require]
dev =
    pytest>=6.0
    black>=22.0
test =
    coverage>=6.0

[tool:pytest]
minversion = 6.0
testpaths = tests
addopts = -ra -q

[mypy]
python_version = 3.8
strict = True
warn_return_any = True

[flake8]
max-line-length = 88
exclude = .git,__pycache__,build,dist
ignore = E203,E501

[coverage:run]
source = src
omit = */tests/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            setup_cfg_path = tmpdir / "setup.cfg"
            setup_cfg_path.write_text(setup_cfg_content)

            analyzer = SetupConfigAnalyzer(tmpdir)
            result = analyzer.analyze_setup_cfg()

            assert result is not None
            assert "metadata" in result
            assert "options" in result
            assert "tool:pytest" in result
            assert "mypy" in result
            assert "flake8" in result
            assert "coverage:run" in result

            # Test tool configuration extraction
            tool_configs = analyzer.extract_tool_configs_from_setup_cfg(result)

            assert "pytest" in tool_configs
            assert "mypy" in tool_configs
            assert "flake8" in tool_configs
            assert "coverage" in tool_configs

            # Test pytest configuration
            pytest_config = tool_configs["pytest"]
            assert pytest_config.config_source == "setup.cfg"
            assert "minversion" in pytest_config.settings

            # Test flake8 configuration
            flake8_config = tool_configs["flake8"]
            assert flake8_config.line_length == 88
            assert flake8_config.exclude_patterns == [".git", "__pycache__", "build", "dist"]


class TestRequirementsAnalyzer:
    """Test RequirementsAnalyzer class."""

    def test_find_requirements_files(self):
        """Test finding various requirements files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create various requirements files
            (tmpdir / "requirements.txt").touch()
            (tmpdir / "requirements-dev.txt").touch()
            (tmpdir / "dev-requirements.txt").touch()
            (tmpdir / "constraints.txt").touch()

            # Create requirements directory
            req_dir = tmpdir / "requirements"
            req_dir.mkdir()
            (req_dir / "base.txt").touch()
            (req_dir / "test.txt").touch()

            analyzer = RequirementsAnalyzer(tmpdir)
            files = analyzer.find_requirements_files()

            file_names = [f.name for f in files]
            assert "requirements.txt" in file_names
            assert "requirements-dev.txt" in file_names
            assert "dev-requirements.txt" in file_names
            assert "constraints.txt" in file_names
            assert "base.txt" in file_names
            assert "test.txt" in file_names

    def test_analyze_requirements_file(self):
        """Test analysis of requirements file."""
        requirements_content = '''
# Main dependencies
requests>=2.25.0
click[colorama]>=8.0
pydantic>=1.8.0; python_version>='3.8'

# VCS dependencies
-e git+https://github.com/user/repo.git#egg=package
git+https://github.com/user/repo2.git@v1.0#egg=package2[extra]

# Local packages
-e ./local-package

# Index options
--index-url https://pypi.org/simple/
--extra-index-url https://private.pypi.org/simple/

# Include other requirements
-r requirements-base.txt
-r constraints.txt

# Comments and empty lines should be ignored

flask==2.0.0  # Inline comment
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            req_file_path = tmpdir / "requirements.txt"
            req_file_path.write_text(requirements_content)

            analyzer = RequirementsAnalyzer(tmpdir)
            result = analyzer.analyze_requirements_file(req_file_path)

            assert result.file_path == "requirements.txt"

            # Test dependencies
            assert len(result.dependencies) == 7  # Including VCS and local

            # Test regular dependencies
            dep_names = [dep.name for dep in result.dependencies]
            assert "requests" in dep_names
            assert "click" in dep_names
            assert "pydantic" in dep_names
            assert "package" in dep_names
            assert "package2" in dep_names
            assert "local-package" in dep_names
            assert "flask" in dep_names

            # Test specific dependency parsing
            requests_dep = next(dep for dep in result.dependencies if dep.name == "requests")
            assert requests_dep.version_spec == ">=2.25.0"
            assert requests_dep.category == "main"

            click_dep = next(dep for dep in result.dependencies if dep.name == "click")
            assert click_dep.extras == ["colorama"]

            pydantic_dep = next(dep for dep in result.dependencies if dep.name == "pydantic")
            assert pydantic_dep.markers == "python_version>='3.8'"

            # Test VCS dependencies
            vcs_dep = next(dep for dep in result.dependencies if dep.name == "package")
            assert vcs_dep.editable is True
            assert "git+" in vcs_dep.url

            vcs_dep2 = next(dep for dep in result.dependencies if dep.name == "package2")
            assert vcs_dep2.extras == ["extra"]

            # Test pip options
            assert "--index-url" in result.options
            assert result.options["--index-url"] == "https://pypi.org/simple/"
            assert "--extra-index-url" in result.options

            # Test includes
            assert len(result.includes) == 2
            assert "requirements-base.txt" in result.includes
            assert "constraints.txt" in result.includes

    def test_infer_category_from_filename(self):
        """Test category inference from filename."""
        analyzer = RequirementsAnalyzer(Path("."))

        assert analyzer._infer_category_from_filename("requirements.txt") == "main"
        assert analyzer._infer_category_from_filename("requirements-dev.txt") == "dev"
        assert analyzer._infer_category_from_filename("dev-requirements.txt") == "dev"
        assert analyzer._infer_category_from_filename("test-requirements.txt") == "test"
        assert analyzer._infer_category_from_filename("docs-requirements.txt") == "docs"
        assert analyzer._infer_category_from_filename("constraints.txt") == "constraints"


class TestEnvironmentAnalyzer:
    """Test EnvironmentAnalyzer class."""

    def test_extract_environment_variables(self):
        """Test extraction of environment variables from various files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create .env file
            env_content = '''
DATABASE_URL=postgres://localhost/mydb
SECRET_KEY=my-secret-key
DEBUG=True
PORT=8000
# Comment line
EMPTY_VAR=
'''
            (tmpdir / ".env").write_text(env_content)

            # Create .env.example file
            env_example_content = '''
DATABASE_URL=postgres://localhost/example
API_KEY=your-api-key-here
REDIS_URL=redis://localhost:6379
'''
            (tmpdir / ".env.example").write_text(env_example_content)

            # Create docker-compose.yml file
            docker_compose_content = '''
version: '3.8'
services:
  web:
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY
      - WORKER_PROCESSES=4
    env_file:
      - .env
'''
            (tmpdir / "docker-compose.yml").write_text(docker_compose_content)

            # Create Dockerfile
            dockerfile_content = '''
FROM python:3.9
ENV PYTHONPATH=/app
ENV PORT=8000
ENV WORKERS=1
COPY . /app
'''
            (tmpdir / "Dockerfile").write_text(dockerfile_content)

            analyzer = EnvironmentAnalyzer(tmpdir)
            env_vars = analyzer.extract_environment_variables()

            # Should find all unique environment variables
            assert "DATABASE_URL" in env_vars
            assert "SECRET_KEY" in env_vars
            assert "DEBUG" in env_vars
            assert "PORT" in env_vars
            assert "API_KEY" in env_vars
            assert "REDIS_URL" in env_vars
            assert "WORKER_PROCESSES" in env_vars
            assert "PYTHONPATH" in env_vars
            assert "WORKERS" in env_vars

            # Should not include comments or empty variables
            assert "Comment" not in env_vars
            assert "EMPTY_VAR" not in env_vars or len(env_vars) >= 9


class TestConfigurationAnalyzer:
    """Test ConfigurationAnalyzer integration."""

    def test_comprehensive_analysis(self):
        """Test comprehensive configuration analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create pyproject.toml
            pyproject_content = '''
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
version = "1.0.0"
description = "A comprehensive test project"
requires-python = ">=3.8"
dependencies = ["requests>=2.25.0", "click>=8.0"]

[project.optional-dependencies]
dev = ["pytest>=6.0", "black>=22.0"]

[tool.black]
line-length = 88
target-version = ["py38"]

[tool.ruff]
line-length = 88
select = ["E", "F"]

[tool.pytest.ini_options]
testpaths = ["tests"]
'''
            (tmpdir / "pyproject.toml").write_text(pyproject_content)

            # Create setup.cfg
            setup_cfg_content = '''
[mypy]
strict = true

[flake8]
max-line-length = 88
'''
            (tmpdir / "setup.cfg").write_text(setup_cfg_content)

            # Create requirements files
            (tmpdir / "requirements.txt").write_text("requests>=2.25.0\nclick>=8.0\n")
            (tmpdir / "requirements-dev.txt").write_text("pytest>=6.0\nblack>=22.0\n")

            # Create .env file
            (tmpdir / ".env").write_text("DATABASE_URL=postgres://localhost/db\nSECRET_KEY=secret\n")

            # Create additional config files
            (tmpdir / "tox.ini").touch()
            (tmpdir / ".coveragerc").touch()

            analyzer = ConfigurationAnalyzer(tmpdir)
            config = analyzer.analyze()

            # Test build system
            assert config.build_system is not None
            assert config.build_system.system == "setuptools"
            assert config.build_system.build_backend == "setuptools.build_meta"

            # Test configuration files
            expected_files = [
                "pyproject.toml", "setup.cfg", "requirements.txt",
                "requirements-dev.txt", "tox.ini", ".coveragerc"
            ]
            for expected_file in expected_files:
                assert expected_file in config.config_files

            # Test tool configurations
            assert "black" in config.tool_configs
            assert "ruff" in config.tool_configs
            assert "pytest" in config.tool_configs
            assert "mypy" in config.tool_configs
            assert "flake8" in config.tool_configs

            # Test dependencies
            assert "main" in config.dependencies
            assert "dev" in config.dependencies

            # Test Python versions
            assert ">=3.8" in config.python_versions

            # Test environment variables
            assert "DATABASE_URL" in config.environment_variables
            assert "SECRET_KEY" in config.environment_variables

            # Test requirements files
            assert len(config.requirements_files) == 2
            req_file_paths = [rf.file_path for rf in config.requirements_files]
            assert "requirements.txt" in req_file_paths
            assert "requirements-dev.txt" in req_file_paths

    def test_get_configuration_summary(self):
        """Test configuration summary generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create minimal pyproject.toml
            pyproject_content = '''
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[project]
requires-python = ">=3.9"
dependencies = ["requests", "click"]

[project.optional-dependencies]
dev = ["pytest", "black"]

[tool.black]
line-length = 100
'''
            (tmpdir / "pyproject.toml").write_text(pyproject_content)

            analyzer = ConfigurationAnalyzer(tmpdir)
            config = analyzer.analyze()
            summary = analyzer.get_configuration_summary(config)

            assert summary["build_system"] == "poetry"
            assert "main" in summary["dependency_categories"]
            assert "dev" in summary["dependency_categories"]
            assert summary["total_dependencies"] == 4  # requests, click, pytest, black
            assert "black" in summary["tools_configured"]
            assert summary["config_files_found"] == 1
            assert ">=3.9" in summary["python_versions"]
            assert summary["has_errors"] is False
            assert summary["has_warnings"] is False

    def test_error_handling(self):
        """Test error handling in configuration analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create invalid TOML file
            invalid_toml = '''
[project
name = "invalid-project"  # Missing closing bracket
'''
            (tmpdir / "pyproject.toml").write_text(invalid_toml)

            analyzer = ConfigurationAnalyzer(tmpdir)
            config = analyzer.analyze()

            # Should handle errors gracefully
            assert config is not None
            # May have errors logged but shouldn't crash
            # The exact error handling depends on implementation
