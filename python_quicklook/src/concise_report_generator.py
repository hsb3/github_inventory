"""
Concise report generator for Python Quick Look tool.
Focuses on answering 3 core codebase questions with visual diagrams.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .python_quicklook import PythonQuickLook

from mermaid_generator import MermaidGenerator, MermaidConfig

logger = logging.getLogger(__name__)


@dataclass
class ConciseReportConfig:
    """Configuration for concise report generation."""

    max_classes_shown: int = 20
    max_functions_shown: int = 15
    show_private_methods: bool = False
    include_io_patterns: bool = True
    target_read_time_minutes: int = 5


class ConciseReportGenerator:
    """Generates concise reports focused on codebase structure understanding."""

    def __init__(self, analyzer: "PythonQuickLook", config: Optional[ConciseReportConfig] = None):
        """Initialize concise report generator.

        Args:
            analyzer: PythonQuickLook instance with analyzed modules
            config: Configuration for report generation
        """
        self.analyzer = analyzer
        self.config = config or ConciseReportConfig()
        self.stats = analyzer.get_statistics()

        # Initialize Mermaid generator
        mermaid_config = MermaidConfig(
            max_classes_per_diagram=self.config.max_classes_shown,
            show_private_methods=self.config.show_private_methods
        )
        self.mermaid_generator = MermaidGenerator(analyzer, mermaid_config)

    def generate(self) -> str:
        """Generate concise codebase analysis report."""
        sections = []

        # Header
        project_name = self.analyzer.target_dir.name
        sections.append(f"# 🔍 {project_name} - Quick Codebase Analysis")
        sections.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} • Target read time: {self.config.target_read_time_minutes} minutes*\n")

        # Generate Mermaid diagrams
        mermaid_result = self.mermaid_generator.generate_diagrams()

        # Question 1: What classes and methods are in this project?
        sections.append(self._generate_class_inventory(mermaid_result))

        # Question 2: How are classes related to each other?
        sections.append(self._generate_class_relationships(mermaid_result))

        # Question 3: What functions exist and how do they relate to classes and I/O?
        sections.append(self._generate_function_analysis(mermaid_result))

        # Quick stats summary
        sections.append(self._generate_quick_stats())

        return "\n\n".join(sections)

    def _generate_class_inventory(self, mermaid_result) -> str:
        """Generate section answering: What classes and methods are in this project?"""
        lines = ["## 1. 📚 What classes and methods are in this project?"]

        # Add class diagram
        if mermaid_result.success and mermaid_result.class_diagram_mermaid:
            lines.append("### Class Structure Overview")
            lines.append(mermaid_result.class_diagram_mermaid)

        # Key classes summary
        lines.append("### 🎯 Key Classes")

        all_classes = []
        for module in self.analyzer.modules:
            for class_info in module.classes:
                all_classes.append((module.name, class_info))

        # Sort by number of methods (most important first)
        all_classes.sort(key=lambda x: len(x[1].methods), reverse=True)

        for i, (module_name, class_info) in enumerate(all_classes[:self.config.max_classes_shown]):
            method_count = len(class_info.methods)
            public_methods = [m for m in class_info.methods if not m.name.startswith('_')]

            lines.append(f"- **{class_info.name}** ({module_name}) • {method_count} methods")
            if class_info.docstring:
                # Get first line of docstring
                first_line = class_info.docstring.split('\n')[0].strip()
                lines.append(f"  *{first_line}*")

            # Show key methods
            if public_methods:
                key_methods = [m.name for m in public_methods[:3]]
                lines.append(f"  Key methods: `{'`, `'.join(key_methods)}`")

        return "\n".join(lines)

    def _generate_class_relationships(self, mermaid_result) -> str:
        """Generate section answering: How are classes related to each other?"""
        lines = ["## 2. 🔗 How are classes related to each other?"]

        # Add relationship diagram
        if mermaid_result.success and mermaid_result.relationship_diagram_mermaid:
            lines.append("### Module Dependencies")
            lines.append(mermaid_result.relationship_diagram_mermaid)

        # Add module overview
        if mermaid_result.success and mermaid_result.module_overview_mermaid:
            lines.append("### Module Organization")
            lines.append(mermaid_result.module_overview_mermaid)

        # Inheritance relationships
        inheritance_found = False
        for module in self.analyzer.modules:
            for class_info in module.classes:
                if class_info.bases:
                    if not inheritance_found:
                        lines.append("### 🧬 Inheritance Relationships")
                        inheritance_found = True
                    for base in class_info.bases:
                        lines.append(f"- **{class_info.name}** extends `{base}`")

        # Dependency insights
        if hasattr(self.analyzer, 'dependency_analysis') and self.analyzer.dependency_analysis:
            dep_analysis = self.analyzer.dependency_analysis
            if dep_analysis.dependency_graph.circular_dependencies:
                lines.append("### ⚠️ Circular Dependencies")
                for cycle in dep_analysis.dependency_graph.circular_dependencies[:3]:  # Show first 3
                    cycle_str = " → ".join(cycle + [cycle[0]])
                    lines.append(f"- `{cycle_str}`")

        return "\n".join(lines)

    def _generate_function_analysis(self, mermaid_result) -> str:
        """Generate section answering: What functions exist and how do they relate to classes and I/O?"""
        lines = ["## 3. ⚡ What functions exist and how do they relate to classes and I/O?"]

        # Standalone functions (not in classes)
        standalone_functions = []
        for module in self.analyzer.modules:
            for func in module.functions:
                standalone_functions.append((module.name, func))

        if standalone_functions:
            lines.append("### 🔧 Standalone Functions")
            for module_name, func in standalone_functions[:self.config.max_functions_shown]:
                lines.append(f"- **{func.name}()** ({module_name})")
                if func.docstring:
                    first_line = func.docstring.split('\n')[0].strip()
                    lines.append(f"  *{first_line}*")

        # I/O Patterns Analysis
        if self.config.include_io_patterns:
            lines.append("### 📁 I/O Patterns")
            io_patterns = self._analyze_io_patterns()

            if io_patterns['file_readers']:
                lines.append(f"**File Readers:** {', '.join(io_patterns['file_readers'])}")
            if io_patterns['file_writers']:
                lines.append(f"**File Writers:** {', '.join(io_patterns['file_writers'])}")
            if io_patterns['cli_interfaces']:
                lines.append(f"**CLI Interfaces:** {', '.join(io_patterns['cli_interfaces'])}")
            if io_patterns['data_processors']:
                lines.append(f"**Data Processors:** {', '.join(io_patterns['data_processors'])}")

        # Method distribution
        lines.append("### 📊 Method Distribution")
        total_methods = sum(len(c.methods) for m in self.analyzer.modules for c in m.classes)
        total_functions = len(standalone_functions)
        lines.append(f"- **Class methods:** {total_methods}")
        lines.append(f"- **Standalone functions:** {total_functions}")
        lines.append(f"- **Total callable units:** {total_methods + total_functions}")

        return "\n".join(lines)

    def _analyze_io_patterns(self) -> Dict[str, List[str]]:
        """Analyze I/O patterns in the codebase."""
        patterns = {
            'file_readers': [],
            'file_writers': [],
            'cli_interfaces': [],
            'data_processors': []
        }

        # Keywords that suggest I/O operations
        read_keywords = ['read', 'load', 'parse', 'import', 'fetch', 'get']
        write_keywords = ['write', 'save', 'export', 'generate', 'create', 'output']
        cli_keywords = ['main', 'cli', 'command', 'arg', 'parser']
        process_keywords = ['process', 'analyze', 'transform', 'convert', 'format']

        all_functions = []
        # Get all functions from all modules
        for module in self.analyzer.modules:
            # Add standalone functions
            for func in module.functions:
                all_functions.append(func.name)
            # Add methods from classes
            for class_info in module.classes:
                for method in class_info.methods:
                    all_functions.append(f"{class_info.name}.{method.name}")

        for func_name in all_functions:
            name_lower = func_name.lower()

            # Check for file reading patterns
            if any(keyword in name_lower for keyword in read_keywords):
                patterns['file_readers'].append(func_name)

            # Check for file writing patterns
            if any(keyword in name_lower for keyword in write_keywords):
                patterns['file_writers'].append(func_name)

            # Check for CLI patterns
            if any(keyword in name_lower for keyword in cli_keywords):
                patterns['cli_interfaces'].append(func_name)

            # Check for data processing patterns
            if any(keyword in name_lower for keyword in process_keywords):
                patterns['data_processors'].append(func_name)

        # Limit results to keep report concise
        for key in patterns:
            patterns[key] = patterns[key][:5]  # Show max 5 examples

        return patterns

    def _generate_quick_stats(self) -> str:
        """Generate quick statistics summary."""
        lines = ["## 📊 Quick Statistics"]

        lines.append("| Metric | Count |")
        lines.append("|--------|-------|")
        lines.append(f"| Modules | {self.stats['modules']} |")
        lines.append(f"| Classes | {self.stats['classes']} |")
        lines.append(f"| Functions | {self.stats['functions']} |")
        lines.append(f"| Methods | {self.stats['methods']} |")

        # Documentation coverage
        if self.stats['classes'] > 0:
            class_doc_pct = (self.stats['documented_classes'] / self.stats['classes']) * 100
            lines.append(f"| Documented Classes | {class_doc_pct:.0f}% |")

        if self.stats['functions'] > 0:
            func_doc_pct = (self.stats['documented_functions'] / self.stats['functions']) * 100
            lines.append(f"| Documented Functions | {func_doc_pct:.0f}% |")

        lines.append("")
        lines.append("*This analysis provides a structural overview of the codebase for quick understanding.*")

        return "\n".join(lines)


def main():
    """Test the concise report generator."""
    from python_quicklook import PythonQuickLook

    # Analyze current project
    analyzer = PythonQuickLook('src')
    analyzer.analyze_project()

    # Generate concise report
    generator = ConciseReportGenerator(analyzer)
    report = generator.generate()

    print(report)

    # Save to file
    with open('concise_analysis_report.md', 'w') as f:
        f.write(report)
    print("\nReport saved to: concise_analysis_report.md")


if __name__ == "__main__":
    main()
