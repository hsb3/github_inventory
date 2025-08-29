"""
Tests for dependency analyzer functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock
import pytest

from src.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyInfo,
    ModuleDependencyGraph,
    DependencyAnalysisResult
)
from src.python_quicklook import ModuleInfo


class TestDependencyInfo:
    """Test DependencyInfo dataclass."""

    def test_dependency_info_creation(self):
        """Test creating DependencyInfo objects."""
        dep = DependencyInfo(
            name="requests",
            dependency_type="external",
            import_type="module",
            source_module="main",
            import_statement="import requests"
        )

        assert dep.name == "requests"
        assert dep.dependency_type == "external"
        assert dep.import_type == "module"
        assert dep.source_module == "main"
        assert dep.import_statement == "import requests"
        assert dep.resolved_path is None
        assert dep.imported_items == []


class TestDependencyAnalyzer:
    """Test DependencyAnalyzer class."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            yield project_path

    @pytest.fixture
    def analyzer(self, temp_project):
        """Create a DependencyAnalyzer instance."""
        return DependencyAnalyzer(temp_project)

    def test_analyzer_initialization(self, analyzer, temp_project):
        """Test analyzer initialization."""
        assert analyzer.project_root == temp_project
        assert isinstance(analyzer.stdlib_modules, set)
        assert "os" in analyzer.stdlib_modules
        assert "sys" in analyzer.stdlib_modules
        assert "json" in analyzer.stdlib_modules

    def test_parse_simple_import(self, analyzer):
        """Test parsing simple import statements."""
        import_statement = "import os"
        deps = analyzer._parse_import_statement(import_statement, "main")

        assert len(deps) == 1
        assert deps[0].name == "os"
        assert deps[0].import_type == "module"
        assert deps[0].source_module == "main"
        assert deps[0].import_statement == "import os"

    def test_parse_from_import(self, analyzer):
        """Test parsing from import statements."""
        import_statement = "from pathlib import Path"
        deps = analyzer._parse_import_statement(import_statement, "main")

        assert len(deps) == 1
        assert deps[0].name == "pathlib"
        assert deps[0].import_type == "from_import"
        assert deps[0].imported_items == ["Path"]

    def test_parse_multiple_imports(self, analyzer):
        """Test parsing multiple imports in one statement."""
        import_statement = "import os, sys, json"
        deps = analyzer._parse_import_statement(import_statement, "main")

        assert len(deps) == 3
        assert deps[0].name == "os"
        assert deps[1].name == "sys"
        assert deps[2].name == "json"

    def test_parse_relative_import(self, analyzer):
        """Test parsing relative import statements."""
        import_statement = "from .utils import helper"
        deps = analyzer._parse_import_statement(import_statement, "package.main")

        assert len(deps) == 1
        assert deps[0].name == ".utils"
        assert deps[0].import_type == "relative"
        assert deps[0].imported_items == ["helper"]

    def test_parse_alias_import(self, analyzer):
        """Test parsing import with alias."""
        import_statement = "import numpy as np"
        deps = analyzer._parse_import_statement(import_statement, "main")

        assert len(deps) == 1
        assert deps[0].name == "numpy"  # Original name, not alias
        assert deps[0].import_type == "module"

    def test_resolve_relative_import_same_level(self, analyzer):
        """Test resolving same-level relative imports."""
        resolved = analyzer._resolve_relative_import(".utils", "package.main")
        assert resolved == "package.utils"

    def test_resolve_relative_import_parent_level(self, analyzer):
        """Test resolving parent-level relative imports."""
        resolved = analyzer._resolve_relative_import("..common", "package.subpackage.main")
        assert resolved == "package.common"

    def test_resolve_relative_import_multiple_levels(self, analyzer):
        """Test resolving multiple-level relative imports."""
        resolved = analyzer._resolve_relative_import("...root", "package.sub1.sub2.main")
        assert resolved == "package.root"  # ... goes up 2 levels from sub2 -> package

    def test_classify_dependency_stdlib(self, analyzer):
        """Test classifying standard library dependencies."""
        internal_modules = {"mymodule", "package.submodule"}

        assert analyzer._classify_dependency("os", internal_modules) == "stdlib"
        assert analyzer._classify_dependency("sys", internal_modules) == "stdlib"
        assert analyzer._classify_dependency("json", internal_modules) == "stdlib"

    def test_classify_dependency_internal(self, analyzer):
        """Test classifying internal dependencies."""
        internal_modules = {"mymodule", "package.submodule"}

        assert analyzer._classify_dependency("mymodule", internal_modules) == "internal"
        assert analyzer._classify_dependency("package.submodule", internal_modules) == "internal"

    def test_classify_dependency_external(self, analyzer):
        """Test classifying external dependencies."""
        internal_modules = {"mymodule", "package.submodule"}

        assert analyzer._classify_dependency("requests", internal_modules) == "external"
        assert analyzer._classify_dependency("numpy", internal_modules) == "external"
        assert analyzer._classify_dependency("django", internal_modules) == "external"

    def test_build_module_name_mapping(self, analyzer):
        """Test building module name mapping."""
        modules = [
            ModuleInfo("src.package.module", "src/package/module.py", "Test module", [], [], []),
            ModuleInfo("utils", "utils.py", "Utilities", [], [], []),
            ModuleInfo("main", "main.py", "Main module", [], [], [])
        ]

        mapping = analyzer._build_module_name_mapping(modules)

        # Check direct mappings
        assert mapping["src.package.module"] == "src.package.module"
        assert mapping["utils"] == "utils"
        assert mapping["main"] == "main"

        # Check suffix mappings
        assert mapping["package.module"] == "src.package.module"
        assert mapping["module"] == "src.package.module"

    def test_detect_circular_dependencies_simple(self, analyzer):
        """Test detecting simple circular dependencies."""
        graph = {
            "A": ["B"],
            "B": ["A"]
        }

        cycles = analyzer._detect_circular_dependencies(graph)

        assert len(cycles) == 1
        assert len(cycles[0]) == 3  # A -> B -> A
        assert cycles[0][0] == cycles[0][-1]  # First and last should be the same

    def test_detect_circular_dependencies_complex(self, analyzer):
        """Test detecting complex circular dependencies."""
        graph = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": ["A"]  # Creates cycle A -> B -> D -> A and A -> C -> D -> A
        }

        cycles = analyzer._detect_circular_dependencies(graph)

        assert len(cycles) >= 1  # At least one cycle should be detected

    def test_detect_no_circular_dependencies(self, analyzer):
        """Test when no circular dependencies exist."""
        graph = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": []
        }

        cycles = analyzer._detect_circular_dependencies(graph)

        assert len(cycles) == 0

    def test_calculate_dependency_depth(self, analyzer):
        """Test calculating dependency depths."""
        graph = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": []
        }

        depths = analyzer._calculate_dependency_depth(graph)

        assert depths["D"] == 0  # No dependencies
        assert depths["B"] == 1  # B -> D
        assert depths["C"] == 1  # C -> D
        assert depths["A"] == 2  # A -> B/C -> D

    def test_full_analysis_integration(self, analyzer):
        """Test complete analysis workflow."""
        # Create test modules with various import types
        modules = [
            ModuleInfo(
                "main", "main.py", "Main module",
                imports=["import os", "from pathlib import Path", "import requests", "from .utils import helper"],
                classes=[], functions=[]
            ),
            ModuleInfo(
                "utils", "utils.py", "Utilities",
                imports=["import sys", "from main import something"],
                classes=[], functions=[]
            )
        ]

        result = analyzer.analyze(modules)

        # Check basic structure
        assert isinstance(result, DependencyAnalysisResult)
        assert isinstance(result.dependency_graph, ModuleDependencyGraph)
        assert len(result.all_dependencies) > 0

        # Check statistics are calculated
        assert "total_dependencies" in result.statistics
        assert "internal_dependencies" in result.statistics
        assert "external_dependencies" in result.statistics
        assert "stdlib_dependencies" in result.statistics

        # Check dependencies are classified
        dep_types = [dep.dependency_type for dep in result.all_dependencies]
        assert "stdlib" in dep_types  # os, sys, pathlib
        assert "external" in dep_types  # requests
        assert "internal" in dep_types  # utils <-> main


class TestDependencyAnalysisIntegration:
    """Test integration with actual module analysis."""

    @pytest.fixture
    def sample_project(self):
        """Create a sample project structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create package structure
            package_dir = project_path / "mypackage"
            package_dir.mkdir()

            # Main module
            (package_dir / "__init__.py").write_text("")
            (package_dir / "main.py").write_text("""
import os
import sys
from pathlib import Path
import requests
from .utils import helper_function
from .data import DataProcessor

class MainClass:
    def __init__(self):
        self.processor = DataProcessor()

    def run(self):
        return helper_function()
""")

            # Utils module
            (package_dir / "utils.py").write_text("""
import logging
from typing import Dict, List
from .main import MainClass

def helper_function():
    logger = logging.getLogger(__name__)
    return "helper"

def create_main():
    return MainClass()
""")

            # Data module
            (package_dir / "data.py").write_text("""
import json
import sqlite3
from pathlib import Path

class DataProcessor:
    def __init__(self):
        self.db_path = Path("data.db")

    def process(self):
        return {"status": "ok"}
""")

            yield project_path

    def test_analyze_real_project_structure(self, sample_project):
        """Test analysis on a realistic project structure."""
        from src.python_quicklook import PythonQuickLook

        # Analyze the project
        analyzer = PythonQuickLook(str(sample_project))
        analyzer.analyze_project()

        # Check dependency analysis was performed
        assert analyzer.dependency_analysis is not None

        result = analyzer.dependency_analysis

        # Should have found dependencies
        assert len(result.all_dependencies) > 0

        # Should have classified them correctly
        dep_types = {dep.dependency_type for dep in result.all_dependencies}
        assert "stdlib" in dep_types
        assert "external" in dep_types
        assert "internal" in dep_types

        # Check for circular dependency between main and utils
        if result.dependency_graph.circular_dependencies:
            # There should be a cycle between main and utils
            cycles_str = str(result.dependency_graph.circular_dependencies)
            assert "main" in cycles_str or "utils" in cycles_str

    def test_dependency_statistics_calculation(self, sample_project):
        """Test that dependency statistics are calculated correctly."""
        from src.python_quicklook import PythonQuickLook

        analyzer = PythonQuickLook(str(sample_project))
        analyzer.analyze_project()

        stats = analyzer.dependency_analysis.statistics

        # Basic counts
        assert stats["total_dependencies"] > 0
        assert stats["internal_dependencies"] >= 0
        assert stats["external_dependencies"] >= 0
        assert stats["stdlib_dependencies"] >= 0

        # Total should equal sum of parts
        total = (stats["internal_dependencies"] +
                stats["external_dependencies"] +
                stats["stdlib_dependencies"])
        assert stats["total_dependencies"] == total

        # Depth and fan metrics
        assert "max_dependency_depth" in stats
        assert "avg_dependency_depth" in stats
        assert "max_fan_out" in stats
        assert "avg_fan_out" in stats


class TestErrorHandling:
    """Test error handling in dependency analysis."""

    def test_malformed_import_statements(self):
        """Test handling of malformed import statements."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            analyzer = DependencyAnalyzer(project_path)

            # Test various malformed statements
            malformed_imports = [
                "import",  # Missing module name
                "from import something",  # Missing module name
                "import 123invalid",  # Invalid module name
                "from . import",  # Missing import items
            ]

            for bad_import in malformed_imports:
                # Should not crash, just return empty list or log warning
                deps = analyzer._parse_import_statement(bad_import, "test_module")
                # Should either return empty list or handle gracefully
                assert isinstance(deps, list)

    def test_analysis_with_empty_modules(self):
        """Test analysis when no modules are provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            analyzer = DependencyAnalyzer(project_path)

            result = analyzer.analyze([])

            assert isinstance(result, DependencyAnalysisResult)
            assert len(result.all_dependencies) == 0
            assert result.statistics["total_dependencies"] == 0

    def test_analysis_with_exception(self):
        """Test that analysis handles exceptions gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            analyzer = DependencyAnalyzer(project_path)

            # Create a mock module that might cause issues
            mock_module = Mock()
            mock_module.name = "broken_module"
            mock_module.imports = ["import some.very.long.module.that.might.cause.issues"]

            # Should not crash
            result = analyzer.analyze([mock_module])

            assert isinstance(result, DependencyAnalysisResult)
            # Should have recorded the error or handled it gracefully


if __name__ == "__main__":
    pytest.main([__file__])
