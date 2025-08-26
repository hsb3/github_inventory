"""
Tests for integration with main PythonQuickLook workflow.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.python_quicklook import PythonQuickLook
from src.report_generator import MarkdownReportGenerator


class TestMainWorkflowIntegration:
    """Test integration with the main PythonQuickLook workflow."""

    @pytest.fixture
    def sample_project(self):
        """Create a sample Python project for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "sample_project"
            project_path.mkdir()

            # Create main module
            (project_path / "__init__.py").touch()
            (project_path / "main.py").write_text("""
'''Main application module.'''

class Application:
    '''Main application class with comprehensive features.'''

    def __init__(self, config: dict = None):
        '''Initialize the application.

        Args:
            config: Configuration dictionary
        '''
        self.config = config or {}

    def run(self) -> int:
        '''Run the application.

        Returns:
            Exit code (0 for success)
        '''
        return 0

    @property
    def version(self) -> str:
        '''Get application version.'''
        return "1.0.0"


def main():
    '''Main entry point.'''
    app = Application()
    return app.run()
""")

            # Create utilities module
            (project_path / "utils.py").write_text("""
'''Utility functions for the application.'''

from typing import List, Optional

class Logger:
    '''Simple logging utility.'''

    def __init__(self, name: str):
        self.name = name

    def info(self, message: str) -> None:
        '''Log info message.'''
        print(f"[{self.name}] INFO: {message}")

    def error(self, message: str) -> None:
        '''Log error message.'''
        print(f"[{self.name}] ERROR: {message}")


def parse_config(config_path: str) -> dict:
    '''Parse configuration file.

    Args:
        config_path: Path to configuration file

    Returns:
        Parsed configuration dictionary
    '''
    # Mock implementation
    return {"debug": True}


async def async_operation(data: List[str]) -> Optional[str]:
    '''Perform async operation on data.

    Args:
        data: List of strings to process

    Returns:
        Processed result or None
    '''
    if not data:
        return None
    return data[0].upper()
""")

            yield project_path

    def test_python_quicklook_basic_analysis(self, sample_project):
        """Test basic PythonQuickLook analysis functionality."""
        analyzer = PythonQuickLook(str(sample_project))
        analyzer.analyze_project()

        # Verify analysis results
        assert len(analyzer.modules) >= 2  # main.py and utils.py

        # Check statistics
        stats = analyzer.get_statistics()
        assert stats["modules"] >= 2
        assert stats["classes"] >= 2  # Application and Logger
        assert stats["functions"] >= 3  # main, parse_config, async_operation
        assert stats["methods"] >= 4   # Application methods + Logger methods

        # Verify project context was analyzed
        assert analyzer.project_context is not None

    def test_report_generator_with_diagrams_enabled(self, sample_project):
        """Test report generation with diagrams enabled."""
        analyzer = PythonQuickLook(str(sample_project))
        analyzer.analyze_project()

        # Create report generator with diagrams enabled
        with tempfile.TemporaryDirectory() as temp_output:
            output_dir = Path(temp_output)

            # Mock diagram generation to avoid dependency requirements
            with patch("diagram_generator.DiagramGenerator") as mock_diagram_gen:
                mock_generator = Mock()
                mock_result = Mock()
                mock_result.success = True
                mock_result.class_diagram_path = Path("class_diagram.png")
                mock_result.package_diagram_path = Path("package_diagram.png")
                mock_result.warnings = []
                mock_generator.generate_diagrams.return_value = mock_result
                mock_diagram_gen.return_value = mock_generator

                # Create mock diagram files
                (output_dir / "assets").mkdir(exist_ok=True)
                (output_dir / "assets" / "class_diagram.png").write_bytes(b"fake class diagram")
                (output_dir / "assets" / "package_diagram.png").write_bytes(b"fake package diagram")

                generator = MarkdownReportGenerator(
                    analyzer,
                    output_dir=output_dir,
                    enable_diagrams=True
                )

                # Mock asset copying
                with patch.object(generator.asset_manager, "copy_asset") as mock_copy:
                    def mock_copy_side_effect(src, target, asset_type):
                        # Simulate successful asset copying
                        from src.asset_manager import AssetInfo
                        return AssetInfo(
                            path=output_dir / "assets" / target,
                            asset_type=asset_type,
                            relative_path=Path("assets") / target,
                            created=True
                        )
                    mock_copy.side_effect = mock_copy_side_effect

                    report = generator.generate()

                    # Verify report contains visual elements
                    assert "📊 Visual Project Overview" in report
                    assert "Class Diagram" in report or "visual diagrams" in report.lower()

                    # Verify asset manager was used
                    assert generator.asset_manager is not None

                    # Report should be generated successfully
                    assert len(report) > 100

    def test_report_generator_with_diagrams_disabled(self, sample_project):
        """Test report generation with diagrams disabled."""
        analyzer = PythonQuickLook(str(sample_project))
        analyzer.analyze_project()

        generator = MarkdownReportGenerator(
            analyzer,
            enable_diagrams=False
        )
        report = generator.generate()

        # Should still generate report without diagram sections
        assert "# 🐍 Python Project Quick Look" in report or "Python Project" in report
        assert len(report) > 100  # Should have substantial content

        # Should not have visual overview section
        assert "📊 Visual Project Overview" not in report

        # Diagram generator should not be initialized
        assert generator.diagram_generator is None

    def test_report_generator_handles_diagram_failures_gracefully(self, sample_project):
        """Test report generation handles diagram generation failures gracefully."""
        analyzer = PythonQuickLook(str(sample_project))
        analyzer.analyze_project()

        with tempfile.TemporaryDirectory() as temp_output:
            output_dir = Path(temp_output)

            # Mock diagram generation failure
            with patch("diagram_generator.DiagramGenerator") as mock_diagram_gen:
                mock_generator = Mock()
                mock_result = Mock()
                mock_result.success = False
                mock_result.error_message = "Missing dependencies: pylint"
                mock_result.class_diagram_path = None
                mock_result.package_diagram_path = None
                mock_result.warnings = []
                mock_generator.generate_diagrams.return_value = mock_result
                mock_generator.get_installation_instructions.return_value = {
                    "pylint": "Install with: pip install pylint"
                }
                mock_diagram_gen.return_value = mock_generator

                generator = MarkdownReportGenerator(
                    analyzer,
                    output_dir=output_dir,
                    enable_diagrams=True
                )

                report = generator.generate()

                # Should still generate report
                assert len(report) > 100

                # Should include fallback content
                assert "visual diagrams" in report.lower() or "dependencies" in report.lower()

    def test_asset_manager_integration(self, sample_project):
        """Test asset manager integration in report generation."""
        analyzer = PythonQuickLook(str(sample_project))
        analyzer.analyze_project()

        with tempfile.TemporaryDirectory() as temp_output:
            output_dir = Path(temp_output)

            generator = MarkdownReportGenerator(
                analyzer,
                output_dir=output_dir,
                enable_diagrams=True
            )

            # Verify asset manager is properly initialized
            assert generator.asset_manager is not None
            assert generator.asset_manager.report_dir == output_dir
            assert generator.asset_manager.asset_dir == output_dir / "assets"

            # Test asset directory creation
            assert generator.asset_manager.asset_dir.exists()

            # Test asset management capabilities
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_file.write(b"test asset content")
                temp_path = Path(temp_file.name)

            try:
                # Test asset copying
                asset_info = generator.asset_manager.copy_asset(
                    temp_path,
                    "test_asset.png",
                    "diagram"
                )

                assert asset_info is not None
                assert (output_dir / "assets" / "test_asset.png").exists()

                # Test markdown reference generation
                md_ref = generator.asset_manager.get_markdown_image_ref(
                    "test_asset.png",
                    "Test Asset"
                )
                assert md_ref == "![Test Asset](assets/test_asset.png)"

            finally:
                temp_path.unlink(missing_ok=True)

    def test_end_to_end_workflow_with_output_file(self, sample_project):
        """Test complete end-to-end workflow with file output."""
        analyzer = PythonQuickLook(str(sample_project))
        analyzer.analyze_project()

        with tempfile.TemporaryDirectory() as temp_output:
            output_dir = Path(temp_output)
            report_file = output_dir / "project_analysis.md"

            # Mock diagram generation for consistency
            with patch("diagram_generator.DiagramGenerator") as mock_diagram_gen:
                mock_generator = Mock()
                mock_result = Mock()
                mock_result.success = False  # Simulate missing dependencies
                mock_result.error_message = "Dependencies not available"
                mock_result.class_diagram_path = None
                mock_result.package_diagram_path = None
                mock_result.warnings = []
                mock_generator.generate_diagrams.return_value = mock_result
                mock_generator.get_installation_instructions.return_value = {}
                mock_diagram_gen.return_value = mock_generator

                generator = MarkdownReportGenerator(
                    analyzer,
                    output_dir=output_dir,
                    enable_diagrams=True
                )

                report = generator.generate()

                # Write report to file
                report_file.write_text(report)

                # Verify file was created and has content
                assert report_file.exists()
                assert report_file.stat().st_size > 100

                # Verify report structure
                content = report_file.read_text()
                assert "# 🐍 Python Project Quick Look" in content or "Python Project" in content
                assert "Project Overview" in content or "Project Summary" in content
                assert "Module:" in content or "Classes:" in content

                # Verify project-specific content
                assert "Application" in content  # Class name
                assert "Logger" in content       # Class name
                assert "parse_config" in content  # Function name

    def test_report_generator_handles_missing_project_context(self, sample_project):
        """Test report generation when project context is missing."""
        analyzer = PythonQuickLook(str(sample_project))
        analyzer.analyze_project()

        # Clear project context to simulate missing context
        analyzer.project_context = None

        generator = MarkdownReportGenerator(
            analyzer,
            enable_diagrams=False
        )

        report = generator.generate()

        # Should still generate report
        assert len(report) > 100
        assert "# 🐍 Python Project Quick Look" in report or "Python Project" in report

        # Should handle missing context gracefully and still show module information
        assert "## Module:" in report


class TestMainEntryPoint:
    """Test the main entry point functionality."""

    @pytest.fixture
    def sample_project_for_main(self):
        """Create sample project for main function testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create a simple Python file
            (project_path / "simple.py").write_text("""
'''A simple module for testing.'''

def hello_world():
    '''Print hello world.'''
    print("Hello, World!")

class SimpleClass:
    '''A simple class.'''
    pass
""")

            yield project_path

    def test_main_function_basic_usage(self, sample_project_for_main):
        """Test main function with basic usage."""
        # Mock sys.argv to simulate command line arguments
        with patch("sys.argv", ["python_quicklook.py", str(sample_project_for_main)]):
            with patch("builtins.print") as mock_print:
                # Import and run main
                import src.python_quicklook as python_quicklook
                main = python_quicklook.main

                try:
                    main()

                    # Verify output was generated
                    assert mock_print.called

                    # Check that some expected content was printed
                    printed_content = ""
                    for call in mock_print.call_args_list:
                        if call.args:
                            printed_content += str(call.args[0])

                    assert len(printed_content) > 100
                    assert "Python Project" in printed_content or "hello_world" in printed_content

                except SystemExit:
                    # Main might call sys.exit, which is acceptable
                    pass

    def test_main_function_with_output_file(self, sample_project_for_main):
        """Test main function with output file argument."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as temp_file:
            output_path = temp_file.name

        try:
            # Mock sys.argv to simulate output file argument
            with patch("sys.argv", ["python_quicklook.py", str(sample_project_for_main), "-o", output_path]):
                with patch("builtins.print") as mock_print:
                    import src.python_quicklook as python_quicklook
                    main = python_quicklook.main

                    try:
                        main()

                        # Verify output file was created
                        output_file = Path(output_path)
                        assert output_file.exists()
                        assert output_file.stat().st_size > 100

                        # Verify content
                        content = output_file.read_text()
                        assert "Python Project" in content or "hello_world" in content

                        # Verify success message was printed
                        printed_messages = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
                        success_message_found = any("Report written to" in msg for msg in printed_messages)
                        assert success_message_found

                    except SystemExit:
                        # Acceptable
                        pass

        finally:
            # Clean up
            Path(output_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__])
