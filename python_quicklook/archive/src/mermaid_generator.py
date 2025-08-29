"""
Mermaid diagram generator for Python Quick Look tool.
Generates Mermaid class diagrams that render natively in markdown.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .python_quicklook import ClassInfo, ModuleInfo, PythonQuickLook

logger = logging.getLogger(__name__)


@dataclass
class MermaidConfig:
    """Configuration for Mermaid diagram generation."""

    max_classes_per_diagram: int = 15  # Keep diagrams readable
    show_private_methods: bool = False
    show_method_parameters: bool = False
    group_by_module: bool = True


@dataclass
class MermaidResult:
    """Result of Mermaid diagram generation."""

    success: bool
    class_diagram_mermaid: Optional[str] = None
    relationship_diagram_mermaid: Optional[str] = None
    module_overview_mermaid: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class MermaidGenerator:
    """Generates Mermaid diagrams from Python AST analysis."""

    def __init__(self, analyzer: "PythonQuickLook", config: Optional[MermaidConfig] = None):
        """Initialize Mermaid generator.

        Args:
            analyzer: PythonQuickLook instance with analyzed modules
            config: Configuration for diagram generation
        """
        self.analyzer = analyzer
        self.config = config or MermaidConfig()

    def generate_diagrams(self) -> MermaidResult:
        """Generate all Mermaid diagrams."""
        try:
            result = MermaidResult(success=True)

            # Generate class diagram
            result.class_diagram_mermaid = self._generate_class_diagram()

            # Generate relationship diagram
            result.relationship_diagram_mermaid = self._generate_relationship_diagram()

            # Generate module overview
            result.module_overview_mermaid = self._generate_module_overview()

            return result

        except Exception as e:
            logger.error(f"Failed to generate Mermaid diagrams: {e}")
            return MermaidResult(
                success=False,
                error_message=str(e)
            )

    def _generate_class_diagram(self) -> str:
        """Generate Mermaid class diagram showing classes and their methods."""
        lines = ["```mermaid", "classDiagram"]

        # Get all classes from all modules
        all_classes = []
        for module in self.analyzer.modules:
            for class_info in module.classes:
                all_classes.append((module.name, class_info))

        # Limit number of classes to keep diagram readable
        if len(all_classes) > self.config.max_classes_per_diagram:
            all_classes = all_classes[:self.config.max_classes_per_diagram]

        # Define classes
        for module_name, class_info in all_classes:
            class_name = self._sanitize_name(class_info.name)
            lines.append(f"    class {class_name} {{")

            # Add methods
            for method in class_info.methods:
                if not self.config.show_private_methods and method.name.startswith('_'):
                    continue

                method_signature = method.name
                if self.config.show_method_parameters and method.signature:
                    # Simplify signature for readability
                    params = method.signature.split('(')[1].split(')')[0]
                    if params and params != 'self':
                        method_signature = f"{method.name}({params})"
                    else:
                        method_signature = f"{method.name}()"

                lines.append(f"        {method_signature}")

            lines.append("    }")

        # Add inheritance relationships
        for module_name, class_info in all_classes:
            if class_info.bases:
                for base in class_info.bases:
                    # Only show relationships to classes we're displaying
                    base_name = self._sanitize_name(base)
                    class_name = self._sanitize_name(class_info.name)
                    if any(self._sanitize_name(c[1].name) == base_name for c in all_classes):
                        lines.append(f"    {base_name} <|-- {class_name}")

        lines.append("```")
        return "\n".join(lines)

    def _generate_relationship_diagram(self) -> str:
        """Generate Mermaid diagram showing module relationships."""
        lines = ["```mermaid", "graph TD"]

        # Create nodes for each module
        module_nodes = {}
        for i, module in enumerate(self.analyzer.modules):
            node_id = f"M{i}"
            module_nodes[module.name] = node_id
            lines.append(f"    {node_id}[{module.name}]")

        # Add dependencies if available
        if hasattr(self.analyzer, 'dependency_analysis') and self.analyzer.dependency_analysis:
            dep_graph = self.analyzer.dependency_analysis.dependency_graph

            for module_name, deps in dep_graph.internal_dependencies.items():
                if module_name in module_nodes:
                    source_id = module_nodes[module_name]
                    for dep in deps:
                        if dep in module_nodes:
                            target_id = module_nodes[dep]
                            lines.append(f"    {source_id} --> {target_id}")

        lines.append("```")
        return "\n".join(lines)

    def _generate_module_overview(self) -> str:
        """Generate high-level module overview diagram."""
        lines = ["```mermaid", "graph LR"]

        # Group modules by functionality if possible
        module_groups = self._group_modules()

        for group_name, modules in module_groups.items():
            # Create a subgraph for each group
            lines.append(f"    subgraph {group_name}")
            for module in modules:
                node_id = self._sanitize_name(module.name)
                class_count = len(module.classes)
                func_count = len(module.functions)
                lines.append(f"        {node_id}[{module.name}<br/>{class_count}c, {func_count}f]")
            lines.append("    end")

        lines.append("```")
        return "\n".join(lines)

    def _group_modules(self) -> Dict[str, List["ModuleInfo"]]:
        """Group modules by functionality based on names."""
        groups = {
            "Core": [],
            "Analysis": [],
            "Generation": [],
            "Utilities": []
        }

        for module in self.analyzer.modules:
            name = module.name.lower()
            if 'analyzer' in name or 'analysis' in name:
                groups["Analysis"].append(module)
            elif 'generator' in name or 'report' in name:
                groups["Generation"].append(module)
            elif 'util' in name or 'helper' in name or 'manager' in name:
                groups["Utilities"].append(module)
            else:
                groups["Core"].append(module)

        # Remove empty groups
        return {k: v for k, v in groups.items() if v}

    def _sanitize_name(self, name: str) -> str:
        """Sanitize names for Mermaid compatibility."""
        # Replace problematic characters
        return name.replace('-', '_').replace(' ', '_').replace('.', '_')


def main():
    """Test the Mermaid generator."""
    from python_quicklook import PythonQuickLook

    # Analyze current project
    analyzer = PythonQuickLook('src')
    analyzer.analyze_project()

    # Generate Mermaid diagrams
    generator = MermaidGenerator(analyzer)
    result = generator.generate_diagrams()

    if result.success:
        print("=== CLASS DIAGRAM ===")
        print(result.class_diagram_mermaid)
        print("\n=== RELATIONSHIP DIAGRAM ===")
        print(result.relationship_diagram_mermaid)
        print("\n=== MODULE OVERVIEW ===")
        print(result.module_overview_mermaid)
    else:
        print(f"Failed: {result.error_message}")


if __name__ == "__main__":
    main()
