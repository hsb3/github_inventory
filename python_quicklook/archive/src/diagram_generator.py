"""
Diagram generator for Python Quick Look tool.
Handles UML class diagram generation using pyreverse and Graphviz.
"""

import logging
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .dependency_analyzer import DependencyAnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class DiagramConfig:
    """Configuration for diagram generation."""

    format: str = "png"  # Output format (png, svg, pdf, etc.)
    output_dir: Path = field(default_factory=lambda: Path("assets"))
    class_diagram: bool = True
    package_diagram: bool = True
    dependency_diagram: bool = True  # Generate dependency diagrams
    show_ancestors: int = -1  # Number of ancestor levels to show (-1 for all)
    show_associated: int = -1  # Number of associated levels to show (-1 for all)
    show_builtin: bool = False  # Show builtin objects
    ignore_patterns: List[str] = field(default_factory=lambda: [
        "__pycache__", ".git", ".pytest_cache", ".venv", "venv",
        "node_modules", ".tox", "build", "dist", "*.egg-info"
    ])
    max_modules: int = 50  # Limit number of modules to avoid huge diagrams


@dataclass
class DiagramResult:
    """Result of diagram generation."""

    success: bool
    class_diagram_path: Optional[Path] = None
    package_diagram_path: Optional[Path] = None
    dependency_diagram_path: Optional[Path] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class DiagramGenerator:
    """Generates UML class diagrams using pyreverse."""

    def __init__(self, project_root: Path, config: Optional[DiagramConfig] = None):
        """Initialize diagram generator.

        Args:
            project_root: Root directory of the project to analyze
            config: Configuration for diagram generation
        """
        self.project_root = project_root
        self.config = config or DiagramConfig()
        self._setup_output_dir()

    def _setup_output_dir(self) -> None:
        """Create output directory if it doesn't exist."""
        try:
            # Make output directory relative to project root if it's not absolute
            if not self.config.output_dir.is_absolute():
                self.config.output_dir = self.project_root / self.config.output_dir

            self.config.output_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Output directory prepared: {self.config.output_dir}")
        except Exception as e:
            logger.warning(f"Failed to create output directory {self.config.output_dir}: {e}")

    def check_dependencies(self) -> Tuple[bool, List[str]]:
        """Check if required dependencies are available.

        Returns:
            Tuple of (success, missing_dependencies)
        """
        missing = []

        # Check for pylint (includes pyreverse)
        try:
            result = subprocess.run(
                ["pyreverse", "--help"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                missing.append("pylint")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            missing.append("pylint")

        # Check for Graphviz
        try:
            result = subprocess.run(
                ["dot", "-V"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                missing.append("graphviz")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            missing.append("graphviz")

        return len(missing) == 0, missing

    def _find_python_packages(self) -> List[Path]:
        """Find Python packages in the project."""
        packages = []

        # Look for directories with __init__.py
        for item in self.project_root.rglob("__init__.py"):
            package_dir = item.parent

            # Skip ignored patterns
            if self._should_ignore_path(package_dir):
                continue

            # Avoid nested packages for cleaner diagrams
            if not any(p in package_dir.parents for p in packages):
                packages.append(package_dir)

        # If no packages found, look for .py files in root
        if not packages:
            py_files = list(self.project_root.glob("*.py"))
            if py_files:
                packages.append(self.project_root)

        # Limit number of packages to avoid overwhelming diagrams
        return packages[:self.config.max_modules]

    def _should_ignore_path(self, path: Path) -> bool:
        """Check if path should be ignored based on patterns."""
        path_str = str(path)
        for pattern in self.config.ignore_patterns:
            if pattern in path_str or path.name.startswith("."):
                return True
        return False

    def _build_pyreverse_command(self, target_path: Path, diagram_type: str) -> List[str]:
        """Build pyreverse command with appropriate options.

        Args:
            target_path: Path to analyze
            diagram_type: 'classes' or 'packages'
        """
        cmd = ["pyreverse"]

        # Output format
        cmd.extend(["--output", self.config.format])

        # Output directory
        cmd.extend(["--output-directory", str(self.config.output_dir)])

        # Project name (use directory name)
        project_name = self.project_root.name or "python_project"
        cmd.extend(["--project", project_name])

        # Diagram-specific options
        if diagram_type == "classes":
            if not self.config.show_builtin:
                # Note: pyreverse default is to not show builtins, so we don't need a flag
                pass
            else:
                cmd.append("--show-builtin")

            if self.config.show_ancestors >= 0:
                cmd.extend(["--show-ancestors", str(self.config.show_ancestors)])
            else:
                cmd.append("--all-ancestors")

            if self.config.show_associated >= 0:
                cmd.extend(["--show-associated", str(self.config.show_associated)])
            else:
                cmd.append("--all-associated")

        # Add target path
        cmd.append(str(target_path))

        return cmd

    def _run_pyreverse(self, target_path: Path, diagram_type: str) -> Tuple[bool, str]:
        """Run pyreverse command.

        Args:
            target_path: Path to analyze
            diagram_type: 'classes' or 'packages'

        Returns:
            Tuple of (success, error_message)
        """
        cmd = self._build_pyreverse_command(target_path, diagram_type)

        try:
            logger.debug(f"Running pyreverse command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # 1 minute timeout
                cwd=self.project_root
            )

            if result.returncode != 0:
                error_msg = f"pyreverse failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                return False, error_msg

            return True, ""

        except subprocess.TimeoutExpired:
            return False, "pyreverse command timed out"
        except Exception as e:
            return False, f"Failed to run pyreverse: {e}"

    def _find_generated_diagram(self, diagram_type: str) -> Optional[Path]:
        """Find the generated diagram file.

        Args:
            diagram_type: 'classes' or 'packages'

        Returns:
            Path to diagram file if found
        """
        project_name = self.project_root.name or "python_project"
        filename = f"{diagram_type}_{project_name}.{self.config.format}"
        diagram_path = self.config.output_dir / filename

        if diagram_path.exists():
            return diagram_path

        # Try alternative naming patterns
        alt_patterns = [
            f"{diagram_type}.{self.config.format}",
            f"classes.{self.config.format}" if diagram_type == "classes" else f"packages.{self.config.format}",
            f"{project_name}_{diagram_type}.{self.config.format}",
        ]

        for pattern in alt_patterns:
            alt_path = self.config.output_dir / pattern
            if alt_path.exists():
                return alt_path

        return None

    def generate_class_diagram(self) -> Tuple[bool, Optional[Path], str]:
        """Generate UML class diagram.

        Returns:
            Tuple of (success, diagram_path, error_message)
        """
        if not self.config.class_diagram:
            return True, None, "Class diagram generation disabled"

        packages = self._find_python_packages()
        if not packages:
            return False, None, "No Python packages found to analyze"

        # Use the first/main package for diagram generation
        target_package = packages[0]

        success, error_msg = self._run_pyreverse(target_package, "classes")
        if not success:
            return False, None, error_msg

        diagram_path = self._find_generated_diagram("classes")
        if not diagram_path:
            return False, None, "Generated class diagram file not found"

        return True, diagram_path, ""

    def generate_package_diagram(self) -> Tuple[bool, Optional[Path], str]:
        """Generate UML package diagram.

        Returns:
            Tuple of (success, diagram_path, error_message)
        """
        if not self.config.package_diagram:
            return True, None, "Package diagram generation disabled"

        packages = self._find_python_packages()
        if not packages:
            return False, None, "No Python packages found to analyze"

        # For package diagrams, analyze the project root or main package
        target_path = self.project_root
        if len(packages) == 1 and packages[0] != self.project_root:
            target_path = packages[0]

        success, error_msg = self._run_pyreverse(target_path, "packages")
        if not success:
            return False, None, error_msg

        diagram_path = self._find_generated_diagram("packages")
        if not diagram_path:
            return False, None, "Generated package diagram file not found"

        return True, diagram_path, ""

    def generate_diagrams(self, dependency_analysis: Optional["DependencyAnalysisResult"] = None) -> DiagramResult:
        """Generate all configured diagrams.

        Args:
            dependency_analysis: Optional dependency analysis for dependency diagrams

        Returns:
            DiagramResult with paths to generated diagrams and any errors
        """
        result = DiagramResult(success=True)

        # Check dependencies first
        deps_ok, missing_deps = self.check_dependencies()
        if not deps_ok:
            result.success = False
            result.error_message = f"Missing dependencies: {', '.join(missing_deps)}"
            return result

        # Generate class diagram
        if self.config.class_diagram:
            success, path, error = self.generate_class_diagram()
            if success:
                result.class_diagram_path = path
                if path:
                    logger.info(f"Generated class diagram: {path}")
            else:
                result.warnings.append(f"Class diagram generation failed: {error}")
                logger.warning(f"Class diagram generation failed: {error}")

        # Generate package diagram
        if self.config.package_diagram:
            success, path, error = self.generate_package_diagram()
            if success:
                result.package_diagram_path = path
                if path:
                    logger.info(f"Generated package diagram: {path}")
            else:
                result.warnings.append(f"Package diagram generation failed: {error}")
                logger.warning(f"Package diagram generation failed: {error}")

        # Generate dependency diagram
        if self.config.dependency_diagram and dependency_analysis:
            success, path, error = self.generate_dependency_diagram(dependency_analysis)
            if success:
                result.dependency_diagram_path = path
                if path:
                    logger.info(f"Generated dependency diagram: {path}")
            else:
                result.warnings.append(f"Dependency diagram generation failed: {error}")
                logger.warning(f"Dependency diagram generation failed: {error}")

        # Overall success if at least one diagram was generated or none were requested
        has_diagrams = result.class_diagram_path or result.package_diagram_path or result.dependency_diagram_path
        no_diagrams_requested = (not self.config.class_diagram and
                                 not self.config.package_diagram and
                                 not self.config.dependency_diagram)

        if not has_diagrams and not no_diagrams_requested:
            result.success = False
            if not result.error_message:
                result.error_message = "Failed to generate any diagrams"

        return result

    def get_installation_instructions(self) -> Dict[str, str]:
        """Get installation instructions for missing dependencies.

        Returns:
            Dictionary mapping dependency names to installation instructions
        """
        instructions = {
            "pylint": "Install with: pip install pylint",
            "graphviz": "Install Graphviz:\n"
                      "  - macOS: brew install graphviz\n"
                      "  - Ubuntu/Debian: apt-get install graphviz\n"
                      "  - Windows: Download from https://graphviz.org/download/"
        }

        deps_ok, missing = self.check_dependencies()
        return {dep: instructions[dep] for dep in missing if dep in instructions}

    def _generate_dependency_dot(self, dependency_analysis: "DependencyAnalysisResult") -> str:
        """Generate DOT format for dependency diagram.

        Args:
            dependency_analysis: Result of dependency analysis

        Returns:
            DOT format string for the dependency graph
        """
        lines = []
        lines.append("digraph dependencies {")
        lines.append("    rankdir=TB;")
        lines.append("    node [shape=box, style=rounded];")
        lines.append("    edge [arrowhead=vee];")
        lines.append("")

        graph = dependency_analysis.dependency_graph

        # Define node styles
        lines.append("    // Internal modules")
        for module in graph.all_internal_modules:
            # Use different colors based on dependency depth
            depth = graph.dependency_depth.get(module, 0)
            if depth == 0:
                color = "lightblue"  # Leaf modules
            elif depth <= 2:
                color = "lightgreen"  # Low depth
            else:
                color = "lightyellow"  # High depth

            clean_name = module.replace(".", "_").replace("-", "_")
            display_name = module.split(".")[-1] if "." in module else module
            lines.append(f'    "{clean_name}" [label="{display_name}", fillcolor={color}, style="rounded,filled"];')

        lines.append("")
        lines.append("    // External modules")
        for module in list(graph.all_external_modules)[:20]:  # Limit external modules shown
            clean_name = f"ext_{module.replace('.', '_').replace('-', '_')}"
            display_name = module.split(".")[-1] if "." in module else module
            lines.append(f'    "{clean_name}" [label="{display_name}", fillcolor=lightcoral, style="rounded,filled"];')

        lines.append("")
        lines.append("    // Internal dependencies")
        for source, deps in graph.internal_dependencies.items():
            source_clean = source.replace(".", "_").replace("-", "_")
            for dep in deps:
                dep_clean = dep.replace(".", "_").replace("-", "_")
                lines.append(f'    "{source_clean}" -> "{dep_clean}" [color=blue];')

        lines.append("")
        lines.append("    // External dependencies (sample)")
        external_count = 0
        for source, deps in graph.external_dependencies.items():
            if external_count > 10:  # Limit external dependency edges
                break
            source_clean = source.replace(".", "_").replace("-", "_")
            for dep in deps[:3]:  # Max 3 external deps per module
                dep_clean = f"ext_{dep.replace('.', '_').replace('-', '_')}"
                lines.append(f'    "{source_clean}" -> "{dep_clean}" [color=red, style=dashed];')
                external_count += 1
                if external_count > 10:
                    break

        # Highlight circular dependencies
        if graph.circular_dependencies:
            lines.append("")
            lines.append("    // Circular dependencies")
            for i, cycle in enumerate(graph.circular_dependencies):
                for j in range(len(cycle) - 1):
                    source_clean = cycle[j].replace(".", "_").replace("-", "_")
                    target_clean = cycle[j + 1].replace(".", "_").replace("-", "_")
                    lines.append(f'    "{source_clean}" -> "{target_clean}" [color=red, penwidth=3, label="CYCLE"];')

        lines.append("}")
        return "\n".join(lines)

    def generate_dependency_diagram(self, dependency_analysis: "DependencyAnalysisResult") -> Tuple[bool, Optional[Path], str]:
        """Generate dependency diagram using Graphviz.

        Args:
            dependency_analysis: Result of dependency analysis

        Returns:
            Tuple of (success, diagram_path, error_message)
        """
        if not self.config.dependency_diagram:
            return True, None, "Dependency diagram generation disabled"

        if not dependency_analysis or not dependency_analysis.dependency_graph.all_internal_modules:
            return False, None, "No dependencies found to visualize"

        try:
            # Generate DOT content
            dot_content = self._generate_dependency_dot(dependency_analysis)

            # Create temporary DOT file
            dot_file = self.config.output_dir / "dependencies.dot"
            with open(dot_file, "w", encoding="utf-8") as f:
                f.write(dot_content)

            # Generate diagram using dot command
            project_name = self.project_root.name or "python_project"
            output_file = self.config.output_dir / f"dependencies_{project_name}.{self.config.format}"

            cmd = ["dot", f"-T{self.config.format}", str(dot_file), "-o", str(output_file)]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )

            if result.returncode != 0:
                error_msg = f"Graphviz dot command failed: {result.stderr}"
                return False, None, error_msg

            # Clean up temporary DOT file
            try:
                dot_file.unlink()
            except Exception:
                pass  # Ignore cleanup errors

            if output_file.exists():
                return True, output_file, ""
            else:
                return False, None, "Dependency diagram file was not generated"

        except subprocess.TimeoutExpired:
            return False, None, "Dependency diagram generation timed out"
        except Exception as e:
            return False, None, f"Failed to generate dependency diagram: {e}"


def create_fallback_diagram_content(project_name: str) -> str:
    """Create fallback content when diagram generation fails.

    Args:
        project_name: Name of the project

    Returns:
        Markdown content explaining the situation
    """
    return f"""## 📊 Visual Project Overview

*Visual diagrams are not available for this analysis.*

**Why diagrams might be missing:**
- Missing dependencies (pylint, graphviz)
- Project structure not suitable for diagram generation
- No Python packages with `__init__.py` files found

**To enable visual diagrams:**
1. Install pylint: `pip install pylint`
2. Install Graphviz:
   - macOS: `brew install graphviz`
   - Ubuntu/Debian: `apt-get install graphviz`
   - Windows: Download from https://graphviz.org/download/
3. Ensure your project has proper package structure with `__init__.py` files

**Alternative analysis:**
You can still get comprehensive code analysis from the detailed module sections below.

---
"""


def main():
    """Main entry point for testing diagram generation."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate UML diagrams for Python project")
    parser.add_argument("project_path", nargs="?", default=".", help="Path to Python project")
    parser.add_argument("--output-dir", default="assets", help="Output directory for diagrams")
    parser.add_argument("--format", default="png", help="Output format (png, svg, pdf)")
    parser.add_argument("--no-classes", action="store_true", help="Skip class diagram")
    parser.add_argument("--no-packages", action="store_true", help="Skip package diagram")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Create configuration
    config = DiagramConfig(
        format=args.format,
        output_dir=Path(args.output_dir),
        class_diagram=not args.no_classes,
        package_diagram=not args.no_packages
    )

    # Generate diagrams
    generator = DiagramGenerator(Path(args.project_path), config)
    result = generator.generate_diagrams()

    # Print results
    if result.success:
        print("✅ Diagram generation completed successfully!")
        if result.class_diagram_path:
            print(f"📊 Class diagram: {result.class_diagram_path}")
        if result.package_diagram_path:
            print(f"📦 Package diagram: {result.package_diagram_path}")
    else:
        print(f"❌ Diagram generation failed: {result.error_message}")

        # Show installation instructions if dependencies are missing
        instructions = generator.get_installation_instructions()
        if instructions:
            print("\n📋 Installation instructions:")
            for dep, instruction in instructions.items():
                print(f"{dep}: {instruction}")

    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")


if __name__ == "__main__":
    main()
