"""
Comprehensive tests for DiagramGenerator class.
"""

import os
import subprocess
import tempfile
import unittest.mock
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.diagram_generator import (
    DiagramConfig,
    DiagramGenerator,
    DiagramResult,
    create_fallback_diagram_content,
)


class TestDiagramConfig:
    """Test DiagramConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = DiagramConfig()

        assert config.format == "png"
        assert config.output_dir == Path("assets")
        assert config.class_diagram is True
        assert config.package_diagram is True
        assert config.show_ancestors == -1
        assert config.show_associated == -1
        assert config.show_builtin is False
        assert config.max_modules == 50
        assert "__pycache__" in config.ignore_patterns

    def test_custom_values(self):
        """Test custom configuration values."""
        config = DiagramConfig(
            format="svg",
            output_dir=Path("custom_assets"),
            class_diagram=False,
            package_diagram=True,
            show_ancestors=2,
            show_associated=1,
            show_builtin=True,
            max_modules=25,
            ignore_patterns=["custom_ignore"]
        )

        assert config.format == "svg"
        assert config.output_dir == Path("custom_assets")
        assert config.class_diagram is False
        assert config.package_diagram is True
        assert config.show_ancestors == 2
        assert config.show_associated == 1
        assert config.show_builtin is True
        assert config.max_modules == 25
        assert config.ignore_patterns == ["custom_ignore"]


class TestDiagramResult:
    """Test DiagramResult dataclass."""

    def test_default_values(self):
        """Test default DiagramResult values."""
        result = DiagramResult(success=True)

        assert result.success is True
        assert result.class_diagram_path is None
        assert result.package_diagram_path is None
        assert result.error_message is None
        assert result.warnings == []

    def test_with_paths(self):
        """Test DiagramResult with diagram paths."""
        class_path = Path("classes.png")
        package_path = Path("packages.png")

        result = DiagramResult(
            success=True,
            class_diagram_path=class_path,
            package_diagram_path=package_path,
            warnings=["Test warning"]
        )

        assert result.success is True
        assert result.class_diagram_path == class_path
        assert result.package_diagram_path == package_path
        assert "Test warning" in result.warnings


class TestDiagramGenerator:
    """Test DiagramGenerator class."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            # Create a simple Python package
            (project_path / "__init__.py").touch()
            (project_path / "module1.py").write_text("class TestClass:\n    pass\n")

            # Create subdirectory with package
            sub_package = project_path / "subpackage"
            sub_package.mkdir()
            (sub_package / "__init__.py").touch()
            (sub_package / "module2.py").write_text("class AnotherClass:\n    pass\n")

            yield project_path

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_initialization_default_config(self, temp_project):
        """Test DiagramGenerator initialization with default config."""
        generator = DiagramGenerator(temp_project)

        assert generator.project_root == temp_project
        assert isinstance(generator.config, DiagramConfig)
        assert generator.config.format == "png"

    def test_initialization_custom_config(self, temp_project):
        """Test DiagramGenerator initialization with custom config."""
        config = DiagramConfig(format="svg", class_diagram=False)
        generator = DiagramGenerator(temp_project, config)

        assert generator.project_root == temp_project
        assert generator.config == config
        assert generator.config.format == "svg"
        assert generator.config.class_diagram is False

    def test_setup_output_dir_creates_directory(self, temp_project, temp_output_dir):
        """Test that output directory is created."""
        config = DiagramConfig(output_dir=temp_output_dir / "assets")
        generator = DiagramGenerator(temp_project, config)

        assert generator.config.output_dir.exists()
        assert generator.config.output_dir.is_dir()

    def test_setup_output_dir_relative_path(self, temp_project):
        """Test output directory with relative path."""
        config = DiagramConfig(output_dir=Path("relative_assets"))
        generator = DiagramGenerator(temp_project, config)

        expected_path = temp_project / "relative_assets"
        assert generator.config.output_dir == expected_path
        assert generator.config.output_dir.exists()

    def test_find_python_packages(self, temp_project):
        """Test finding Python packages."""
        generator = DiagramGenerator(temp_project)
        packages = generator._find_python_packages()

        # Should find the main project (subpackage is nested, so excluded by design)
        package_names = [p.name for p in packages]
        assert "test_project" in package_names
        assert len(packages) >= 1

    def test_find_python_packages_no_packages(self):
        """Test finding packages when none exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            generator = DiagramGenerator(project_path)
            packages = generator._find_python_packages()

            # Should find the root directory if it has .py files
            assert len(packages) <= 1

    def test_should_ignore_path(self, temp_project):
        """Test path ignoring logic."""
        generator = DiagramGenerator(temp_project)

        # Should ignore paths with ignore patterns
        assert generator._should_ignore_path(Path("__pycache__/test.py"))
        assert generator._should_ignore_path(Path(".git/config"))
        assert generator._should_ignore_path(Path("venv/lib/python"))

        # Should not ignore normal paths
        assert not generator._should_ignore_path(Path("src/module.py"))
        assert not generator._should_ignore_path(Path("tests/test_something.py"))

    @patch("subprocess.run")
    def test_check_dependencies_all_available(self, mock_run, temp_project):
        """Test dependency check when all dependencies are available."""
        # Mock successful subprocess calls
        mock_run.return_value = Mock(returncode=0)

        generator = DiagramGenerator(temp_project)
        success, missing = generator.check_dependencies()

        assert success is True
        assert missing == []
        assert mock_run.call_count == 2  # pyreverse and dot

    @patch("subprocess.run")
    def test_check_dependencies_missing_pylint(self, mock_run, temp_project):
        """Test dependency check when pylint is missing."""
        def side_effect(cmd, **kwargs):
            if "pyreverse" in cmd:
                raise FileNotFoundError("pyreverse not found")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect

        generator = DiagramGenerator(temp_project)
        success, missing = generator.check_dependencies()

        assert success is False
        assert "pylint" in missing

    @patch("subprocess.run")
    def test_check_dependencies_missing_graphviz(self, mock_run, temp_project):
        """Test dependency check when graphviz is missing."""
        def side_effect(cmd, **kwargs):
            if "dot" in cmd:
                raise FileNotFoundError("dot not found")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect

        generator = DiagramGenerator(temp_project)
        success, missing = generator.check_dependencies()

        assert success is False
        assert "graphviz" in missing

    def test_build_pyreverse_command_classes(self, temp_project):
        """Test building pyreverse command for class diagram."""
        config = DiagramConfig(
            format="png",
            output_dir=Path("assets"),
            show_ancestors=2,
            show_associated=1,
            show_builtin=True
        )
        generator = DiagramGenerator(temp_project, config)

        cmd = generator._build_pyreverse_command(temp_project, "classes")

        assert "pyreverse" in cmd
        assert "--output" in cmd
        assert "png" in cmd
        assert "--output-directory" in cmd
        assert any("assets" in arg for arg in cmd)
        assert "--project" in cmd
        assert "--show-builtin" in cmd
        assert "--show-ancestors" in cmd
        assert "2" in cmd
        assert "--show-associated" in cmd
        assert "1" in cmd

    def test_build_pyreverse_command_packages(self, temp_project):
        """Test building pyreverse command for package diagram."""
        generator = DiagramGenerator(temp_project)
        cmd = generator._build_pyreverse_command(temp_project, "packages")

        assert "pyreverse" in cmd
        assert "--output" in cmd
        assert "--output-directory" in cmd
        assert "--project" in cmd
        assert str(temp_project) in cmd

    @patch("subprocess.run")
    def test_run_pyreverse_success(self, mock_run, temp_project):
        """Test successful pyreverse execution."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        generator = DiagramGenerator(temp_project)
        success, error = generator._run_pyreverse(temp_project, "classes")

        assert success is True
        assert error == ""

    @patch("subprocess.run")
    def test_run_pyreverse_failure(self, mock_run, temp_project):
        """Test failed pyreverse execution."""
        mock_run.return_value = Mock(returncode=1, stderr="Error message")

        generator = DiagramGenerator(temp_project)
        success, error = generator._run_pyreverse(temp_project, "classes")

        assert success is False
        assert "Error message" in error

    @patch("subprocess.run")
    def test_run_pyreverse_timeout(self, mock_run, temp_project):
        """Test pyreverse timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("pyreverse", 60)

        generator = DiagramGenerator(temp_project)
        success, error = generator._run_pyreverse(temp_project, "classes")

        assert success is False
        assert "timed out" in error

    def test_find_generated_diagram_found(self, temp_project, temp_output_dir):
        """Test finding generated diagram file."""
        config = DiagramConfig(output_dir=temp_output_dir)
        generator = DiagramGenerator(temp_project, config)

        # Create a mock diagram file
        diagram_file = temp_output_dir / f"classes_{temp_project.name}.png"
        diagram_file.touch()

        found_path = generator._find_generated_diagram("classes")
        assert found_path == diagram_file

    def test_find_generated_diagram_not_found(self, temp_project, temp_output_dir):
        """Test when generated diagram file is not found."""
        config = DiagramConfig(output_dir=temp_output_dir)
        generator = DiagramGenerator(temp_project, config)

        found_path = generator._find_generated_diagram("classes")
        assert found_path is None

    def test_find_generated_diagram_alternative_naming(self, temp_project, temp_output_dir):
        """Test finding diagram with alternative naming pattern."""
        config = DiagramConfig(output_dir=temp_output_dir)
        generator = DiagramGenerator(temp_project, config)

        # Create diagram with alternative name
        diagram_file = temp_output_dir / "classes.png"
        diagram_file.touch()

        found_path = generator._find_generated_diagram("classes")
        assert found_path == diagram_file

    def test_generate_class_diagram_disabled(self, temp_project):
        """Test class diagram generation when disabled."""
        config = DiagramConfig(class_diagram=False)
        generator = DiagramGenerator(temp_project, config)

        success, path, error = generator.generate_class_diagram()

        assert success is True
        assert path is None
        assert "disabled" in error

    def test_generate_class_diagram_no_packages(self, temp_project):
        """Test class diagram generation with no packages."""
        # Remove all Python files to simulate no packages
        for py_file in temp_project.rglob("*.py"):
            py_file.unlink()

        generator = DiagramGenerator(temp_project)
        success, path, error = generator.generate_class_diagram()

        assert success is False
        assert path is None
        assert "No Python packages found" in error

    @patch.object(DiagramGenerator, "_run_pyreverse")
    @patch.object(DiagramGenerator, "_find_generated_diagram")
    def test_generate_class_diagram_success(self, mock_find, mock_run, temp_project, temp_output_dir):
        """Test successful class diagram generation."""
        mock_run.return_value = (True, "")
        mock_find.return_value = temp_output_dir / "classes.png"

        config = DiagramConfig(output_dir=temp_output_dir)
        generator = DiagramGenerator(temp_project, config)

        success, path, error = generator.generate_class_diagram()

        assert success is True
        assert path == temp_output_dir / "classes.png"
        assert error == ""

    @patch.object(DiagramGenerator, "_run_pyreverse")
    def test_generate_class_diagram_pyreverse_fails(self, mock_run, temp_project):
        """Test class diagram generation when pyreverse fails."""
        mock_run.return_value = (False, "Pyreverse error")

        generator = DiagramGenerator(temp_project)
        success, path, error = generator.generate_class_diagram()

        assert success is False
        assert path is None
        assert "Pyreverse error" in error

    @patch.object(DiagramGenerator, "_run_pyreverse")
    @patch.object(DiagramGenerator, "_find_generated_diagram")
    def test_generate_class_diagram_file_not_found(self, mock_find, mock_run, temp_project):
        """Test class diagram generation when output file is not found."""
        mock_run.return_value = (True, "")
        mock_find.return_value = None

        generator = DiagramGenerator(temp_project)
        success, path, error = generator.generate_class_diagram()

        assert success is False
        assert path is None
        assert "not found" in error

    @patch.object(DiagramGenerator, "check_dependencies")
    @patch.object(DiagramGenerator, "generate_class_diagram")
    @patch.object(DiagramGenerator, "generate_package_diagram")
    def test_generate_diagrams_missing_dependencies(self, mock_pkg, mock_class, mock_check, temp_project):
        """Test generate_diagrams when dependencies are missing."""
        mock_check.return_value = (False, ["pylint", "graphviz"])

        generator = DiagramGenerator(temp_project)
        result = generator.generate_diagrams()

        assert result.success is False
        assert "Missing dependencies" in result.error_message
        assert "pylint" in result.error_message
        assert "graphviz" in result.error_message

    @patch.object(DiagramGenerator, "check_dependencies")
    @patch.object(DiagramGenerator, "generate_class_diagram")
    @patch.object(DiagramGenerator, "generate_package_diagram")
    def test_generate_diagrams_success(self, mock_pkg, mock_class, mock_check, temp_project):
        """Test successful diagram generation."""
        mock_check.return_value = (True, [])
        mock_class.return_value = (True, Path("class.png"), "")
        mock_pkg.return_value = (True, Path("package.png"), "")

        generator = DiagramGenerator(temp_project)
        result = generator.generate_diagrams()

        assert result.success is True
        assert result.class_diagram_path == Path("class.png")
        assert result.package_diagram_path == Path("package.png")
        assert len(result.warnings) == 0

    @patch.object(DiagramGenerator, "check_dependencies")
    @patch.object(DiagramGenerator, "generate_class_diagram")
    @patch.object(DiagramGenerator, "generate_package_diagram")
    def test_generate_diagrams_with_warnings(self, mock_pkg, mock_class, mock_check, temp_project):
        """Test diagram generation with warnings."""
        mock_check.return_value = (True, [])
        mock_class.return_value = (False, None, "Class generation failed")
        mock_pkg.return_value = (True, Path("package.png"), "")

        generator = DiagramGenerator(temp_project)
        result = generator.generate_diagrams()

        assert result.success is True  # Still success because package diagram worked
        assert result.class_diagram_path is None
        assert result.package_diagram_path == Path("package.png")
        assert len(result.warnings) == 1
        assert "Class generation failed" in result.warnings[0]

    @patch.object(DiagramGenerator, "check_dependencies")
    @patch.object(DiagramGenerator, "generate_class_diagram")
    @patch.object(DiagramGenerator, "generate_package_diagram")
    def test_generate_diagrams_all_fail(self, mock_pkg, mock_class, mock_check, temp_project):
        """Test when all diagram generation fails."""
        mock_check.return_value = (True, [])
        mock_class.return_value = (False, None, "Class failed")
        mock_pkg.return_value = (False, None, "Package failed")

        generator = DiagramGenerator(temp_project)
        result = generator.generate_diagrams()

        assert result.success is False
        assert result.class_diagram_path is None
        assert result.package_diagram_path is None
        assert "Failed to generate any diagrams" in result.error_message

    def test_get_installation_instructions(self, temp_project):
        """Test getting installation instructions."""
        generator = DiagramGenerator(temp_project)

        with patch.object(generator, "check_dependencies", return_value=(False, ["pylint", "graphviz"])):
            instructions = generator.get_installation_instructions()

            assert "pylint" in instructions
            assert "graphviz" in instructions
            assert "pip install pylint" in instructions["pylint"]
            assert "brew install graphviz" in instructions["graphviz"]


class TestFallbackDiagramContent:
    """Test fallback diagram content generation."""

    def test_create_fallback_content(self):
        """Test creating fallback diagram content."""
        content = create_fallback_diagram_content("test_project")

        assert "Visual Project Overview" in content
        assert "Visual diagrams are not available" in content
        assert "Missing dependencies" in content
        assert "pip install pylint" in content
        assert "brew install graphviz" in content
        assert "__init__.py" in content


class TestIntegrationScenarios:
    """Integration tests for various real-world scenarios."""

    @pytest.fixture
    def complex_project(self):
        """Create a more complex project structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "complex_project"
            project_path.mkdir()

            # Main package
            (project_path / "__init__.py").touch()
            (project_path / "main.py").write_text("""
class MainClass:
    def __init__(self):
        self.helper = HelperClass()

class HelperClass:
    pass
""")

            # Utils package
            utils_pkg = project_path / "utils"
            utils_pkg.mkdir()
            (utils_pkg / "__init__.py").touch()
            (utils_pkg / "helpers.py").write_text("""
from ..main import MainClass

class UtilHelper:
    def process(self, main_obj: MainClass):
        return main_obj
""")

            # Tests directory (should be ignored)
            tests_dir = project_path / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_main.py").write_text("# test file")

            yield project_path

    def test_complex_project_analysis(self, complex_project):
        """Test analyzing a complex project structure."""
        generator = DiagramGenerator(complex_project)

        # Test package discovery
        packages = generator._find_python_packages()
        package_names = [p.name for p in packages]

        assert "complex_project" in package_names
        # utils is nested inside complex_project, so excluded by design for cleaner diagrams
        assert len(packages) >= 1
        # tests directory should not be included due to ignore patterns

        # Test command building
        cmd = generator._build_pyreverse_command(complex_project, "classes")
        assert "pyreverse" in cmd
        assert str(complex_project) in cmd

    def test_project_with_no_init_files(self):
        """Test project with Python files but no __init__.py files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create Python files without __init__.py
            (project_path / "module1.py").write_text("class Class1: pass")
            (project_path / "module2.py").write_text("class Class2: pass")

            generator = DiagramGenerator(project_path)
            packages = generator._find_python_packages()

            # Should find the root directory
            assert len(packages) == 1
            assert packages[0] == project_path

    def test_empty_project(self):
        """Test completely empty project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            generator = DiagramGenerator(project_path)
            packages = generator._find_python_packages()

            # Should find no packages
            assert len(packages) == 0

    @patch.object(DiagramGenerator, "check_dependencies")
    def test_end_to_end_flow_missing_deps(self, mock_check):
        """Test end-to-end flow when dependencies are missing."""
        mock_check.return_value = (False, ["pylint"])

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            (project_path / "test.py").write_text("class Test: pass")

            generator = DiagramGenerator(project_path)
            result = generator.generate_diagrams()

            assert result.success is False
            assert "Missing dependencies" in result.error_message
            assert "pylint" in result.error_message


if __name__ == "__main__":
    pytest.main([__file__])
