"""
Module dependency analyzer for Python Quick Look tool.
Analyzes import statements to build dependency graphs and detect relationships.
"""

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from .python_quicklook import ModuleInfo

logger = logging.getLogger(__name__)


@dataclass
class DependencyInfo:
    """Information about a single dependency relationship."""

    name: str                           # The imported module/item name
    dependency_type: str                # 'internal', 'external', 'stdlib'
    import_type: str                    # 'module', 'from_import', 'relative'
    source_module: str                  # Which module contains this import
    import_statement: str               # Original import statement
    resolved_path: Optional[str] = None # Resolved module path if internal
    imported_items: List[str] = field(default_factory=list)  # Items imported from module


@dataclass
class ModuleDependencyGraph:
    """Represents the complete dependency graph of a project."""

    internal_dependencies: Dict[str, List[str]] = field(default_factory=dict)  # module -> [dependencies]
    external_dependencies: Dict[str, List[str]] = field(default_factory=dict)  # module -> [external deps]
    stdlib_dependencies: Dict[str, List[str]] = field(default_factory=dict)    # module -> [stdlib deps]
    circular_dependencies: List[List[str]] = field(default_factory=list)       # Cycles found
    dependency_depth: Dict[str, int] = field(default_factory=dict)             # Module -> max depth
    all_internal_modules: Set[str] = field(default_factory=set)                # All internal module names
    all_external_modules: Set[str] = field(default_factory=set)                # All external module names


@dataclass
class DependencyAnalysisResult:
    """Result of dependency analysis with statistics and errors."""

    dependency_graph: ModuleDependencyGraph
    all_dependencies: List[DependencyInfo] = field(default_factory=list)
    statistics: Dict[str, Union[int, float]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class DependencyAnalyzer:
    """Analyzes module dependencies from parsed Python modules."""

    def __init__(self, project_root: Path):
        """Initialize dependency analyzer.

        Args:
            project_root: Root directory of the project being analyzed
        """
        self.project_root = project_root
        self.stdlib_modules = self._get_stdlib_modules()

    def _get_stdlib_modules(self) -> Set[str]:
        """Get set of Python standard library module names."""
        # Common stdlib modules - this is a subset for performance
        # In a production system, you might want to dynamically detect this
        stdlib_modules = {
            'os', 'sys', 'pathlib', 'json', 'yaml', 're', 'ast', 'logging',
            'datetime', 'collections', 'itertools', 'functools', 'typing',
            'dataclasses', 'enum', 'abc', 'contextlib', 'tempfile',
            'subprocess', 'threading', 'multiprocessing', 'asyncio',
            'unittest', 'pytest', 'argparse', 'configparser', 'urllib',
            'http', 'email', 'csv', 'xml', 'html', 'sqlite3', 'pickle',
            'copy', 'math', 'random', 'statistics', 'decimal', 'fractions',
            'hashlib', 'hmac', 'secrets', 'uuid', 'time', 'calendar',
            'zoneinfo', 'locale', 'gettext', 'string', 'textwrap',
            'difflib', 'pprint', 'reprlib', 'warnings', 'traceback',
            'gc', 'weakref', 'types', 'inspect', 'importlib'
        }
        return stdlib_modules

    def _parse_import_statement(self, import_statement: str, source_module: str) -> List[DependencyInfo]:
        """Parse a single import statement into DependencyInfo objects.

        Args:
            import_statement: The import statement string
            source_module: Name of the module containing this import

        Returns:
            List of DependencyInfo objects parsed from the statement
        """
        dependencies = []

        try:
            # Clean up the import statement
            cleaned_import = import_statement.strip()

            if cleaned_import.startswith('import '):
                # Handle "import module" or "import module as alias"
                import_part = cleaned_import[7:].strip()  # Remove "import "

                # Split by comma for multiple imports
                for module_spec in import_part.split(','):
                    module_spec = module_spec.strip()

                    # Handle "as" alias
                    if ' as ' in module_spec:
                        module_name = module_spec.split(' as ')[0].strip()
                    else:
                        module_name = module_spec

                    # Determine if it's a relative import
                    import_type = 'relative' if module_name.startswith('.') else 'module'

                    dependencies.append(DependencyInfo(
                        name=module_name,
                        dependency_type='unknown',  # Will be resolved later
                        import_type=import_type,
                        source_module=source_module,
                        import_statement=cleaned_import,
                        imported_items=[]
                    ))

            elif cleaned_import.startswith('from '):
                # Handle "from module import item" statements
                match = re.match(r'from\s+([^\s]+)\s+import\s+(.+)', cleaned_import)
                if match:
                    module_name = match.group(1)
                    import_items = match.group(2)

                    # Parse imported items
                    items = []
                    for item in import_items.split(','):
                        item = item.strip()
                        # Handle "item as alias"
                        if ' as ' in item:
                            item = item.split(' as ')[0].strip()
                        items.append(item)

                    # Determine if it's a relative import
                    import_type = 'relative' if module_name.startswith('.') else 'from_import'

                    dependencies.append(DependencyInfo(
                        name=module_name,
                        dependency_type='unknown',  # Will be resolved later
                        import_type=import_type,
                        source_module=source_module,
                        import_statement=cleaned_import,
                        imported_items=items
                    ))

        except Exception as e:
            logger.warning(f"Failed to parse import statement '{import_statement}' in {source_module}: {e}")

        return dependencies

    def _resolve_relative_import(self, module_name: str, source_module: str) -> str:
        """Resolve relative import to absolute module name.

        Args:
            module_name: Relative module name (e.g., '..parent.module')
            source_module: Source module containing the import

        Returns:
            Resolved absolute module name
        """
        try:
            # Count leading dots
            dots = 0
            for char in module_name:
                if char == '.':
                    dots += 1
                else:
                    break

            if dots == 0:
                return module_name  # Not a relative import

            # Split source module path
            source_parts = source_module.split('.')

            # Calculate target level
            if dots == 1:
                # Same level: .module -> current_package.module
                if len(source_parts) > 1:
                    base_parts = source_parts[:-1]  # Remove module name, keep package
                else:
                    base_parts = []
            else:
                # Parent levels: ..module -> parent_package.module
                # For ...module from package.sub1.sub2.main, we want to go up 2 levels from current package
                # source_parts = [package, sub1, sub2, main]
                # Remove main (module name) -> [package, sub1, sub2] (current package)
                # dots=3 means go up 2 levels from current package (... = 2 levels up)
                levels_up = dots - 1
                if len(source_parts) > 1:  # Has package structure
                    # Start from package parts (without module name)
                    package_parts = source_parts[:-1]  # [package, sub1, sub2]
                    # Go up the specified number of levels from current package
                    # For ...root: dots=3, levels_up=2
                    # Current package is sub2 (index 2), go up 2 levels means go to parent of package (index -1)
                    # So we need to go up to the parent of the root package
                    target_level = len(package_parts) - levels_up
                    if target_level <= 0:
                        base_parts = []  # Go above root package
                    else:
                        base_parts = package_parts[:target_level]
                else:
                    base_parts = []

            # Construct resolved name
            remaining_name = module_name[dots:] if dots < len(module_name) else ""

            if remaining_name:
                if base_parts:
                    return '.'.join(base_parts + [remaining_name])
                else:
                    return remaining_name
            else:
                return '.'.join(base_parts) if base_parts else ""

        except Exception as e:
            logger.warning(f"Failed to resolve relative import '{module_name}' from '{source_module}': {e}")
            return module_name

    def _classify_dependency(self, module_name: str, internal_modules: Set[str]) -> str:
        """Classify a dependency as internal, external, or stdlib.

        Args:
            module_name: Name of the module to classify
            internal_modules: Set of all internal project module names

        Returns:
            Classification: 'internal', 'external', or 'stdlib'
        """
        # Get the top-level module name
        top_level = module_name.split('.')[0]

        # Check if it's a standard library module
        if top_level in self.stdlib_modules:
            return 'stdlib'

        # Check if it's an internal module (exact match)
        if module_name in internal_modules:
            return 'internal'

        # Check if any internal module starts with this name (for submodules)
        # E.g., module_name="package" and we have "package.submodule"
        for internal_module in internal_modules:
            if internal_module.startswith(module_name + '.'):
                return 'internal'

        # Check if this is a submodule of any internal module
        # E.g., module_name="package.submodule" and we have "package"
        for internal_module in internal_modules:
            if module_name.startswith(internal_module + '.'):
                return 'internal'

        # Also check against the mapping keys (different naming conventions)
        # Check partial matches for different import styles
        module_parts = module_name.split('.')
        for internal_module in internal_modules:
            internal_parts = internal_module.split('.')

            # Check if the internal module ends with the dependency name
            # E.g., module_name="utils" matches internal "mypackage.utils"
            if len(internal_parts) >= len(module_parts):
                if internal_parts[-len(module_parts):] == module_parts:
                    return 'internal'

            # Check if the dependency name ends with the internal module name
            # E.g., module_name="mypackage.utils" matches internal "utils"
            if len(module_parts) >= len(internal_parts):
                if module_parts[-len(internal_parts):] == internal_parts:
                    return 'internal'

        return 'external'

    def _build_module_name_mapping(self, modules: List["ModuleInfo"]) -> Dict[str, str]:
        """Build mapping from import names to module info names.

        Args:
            modules: List of ModuleInfo objects

        Returns:
            Dictionary mapping import names to module names
        """
        mapping = {}

        for module in modules:
            # Add the module name directly
            mapping[module.name] = module.name

            # Add variations for different import styles
            # E.g., for "src.package.module", also add "package.module" and "module"
            parts = module.name.split('.')

            # Add all suffix combinations
            for i in range(len(parts)):
                suffix = '.'.join(parts[i:])
                if suffix not in mapping:  # Don't overwrite existing mappings
                    mapping[suffix] = module.name

            # Also add the base filename without extension as potential import name
            # E.g., for "mypackage/main.py" -> "mypackage.main", also allow "main"
            if len(parts) > 0:
                base_name = parts[-1]
                if base_name not in mapping:
                    mapping[base_name] = module.name

        return mapping

    def _detect_circular_dependencies(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """Detect circular dependencies in the dependency graph.

        Args:
            graph: Dictionary mapping modules to their dependencies

        Returns:
            List of cycles, where each cycle is a list of module names
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> bool:
            """DFS to detect cycles."""
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return True

            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            # Visit all dependencies
            for dependency in graph.get(node, []):
                if dependency in graph:  # Only follow internal dependencies
                    dfs(dependency, path.copy())

            rec_stack.remove(node)
            return False

        # Check each unvisited node
        for node in graph:
            if node not in visited:
                dfs(node, [])

        return cycles

    def _calculate_dependency_depth(self, graph: Dict[str, List[str]]) -> Dict[str, int]:
        """Calculate dependency depth for each module.

        Args:
            graph: Dictionary mapping modules to their dependencies

        Returns:
            Dictionary mapping modules to their maximum dependency depth
        """
        depths = {}
        visited = set()

        def calculate_depth(node: str) -> int:
            """Calculate depth for a single node."""
            if node in visited:
                return depths.get(node, 0)

            visited.add(node)

            # Base case: no dependencies
            dependencies = graph.get(node, [])
            if not dependencies:
                depths[node] = 0
                return 0

            # Recursive case: 1 + max depth of dependencies
            max_dep_depth = 0
            for dep in dependencies:
                if dep in graph:  # Only consider internal dependencies
                    dep_depth = calculate_depth(dep)
                    max_dep_depth = max(max_dep_depth, dep_depth)

            depth = max_dep_depth + 1
            depths[node] = depth
            return depth

        # Calculate depth for all modules
        for module in graph:
            calculate_depth(module)

        return depths

    def analyze(self, modules: List["ModuleInfo"]) -> DependencyAnalysisResult:
        """Analyze dependencies from a list of modules.

        Args:
            modules: List of ModuleInfo objects to analyze

        Returns:
            DependencyAnalysisResult with complete dependency information
        """
        result = DependencyAnalysisResult(
            dependency_graph=ModuleDependencyGraph()
        )

        try:
            # Build mapping of module names for internal resolution
            internal_modules = {module.name for module in modules}
            module_name_mapping = self._build_module_name_mapping(modules)

            # Parse all import statements
            all_dependencies = []

            for module in modules:
                for import_statement in module.imports:
                    parsed_deps = self._parse_import_statement(import_statement, module.name)

                    for dep in parsed_deps:
                        # Resolve relative imports
                        if dep.import_type == 'relative':
                            dep.name = self._resolve_relative_import(dep.name, dep.source_module)

                        # Classify the dependency
                        dep.dependency_type = self._classify_dependency(dep.name, internal_modules)

                        # Resolve internal module paths
                        if dep.dependency_type == 'internal' and dep.name in module_name_mapping:
                            dep.resolved_path = module_name_mapping[dep.name]

                        all_dependencies.append(dep)

            result.all_dependencies = all_dependencies

            # Build dependency graph
            graph = result.dependency_graph

            # Organize dependencies by type
            for dep in all_dependencies:
                source = dep.source_module
                target = dep.resolved_path if dep.resolved_path else dep.name

                if dep.dependency_type == 'internal':
                    if source not in graph.internal_dependencies:
                        graph.internal_dependencies[source] = []
                    if target not in graph.internal_dependencies[source]:
                        graph.internal_dependencies[source].append(target)
                    graph.all_internal_modules.add(target)

                elif dep.dependency_type == 'external':
                    if source not in graph.external_dependencies:
                        graph.external_dependencies[source] = []
                    if target not in graph.external_dependencies[source]:
                        graph.external_dependencies[source].append(target)
                    graph.all_external_modules.add(target)

                elif dep.dependency_type == 'stdlib':
                    if source not in graph.stdlib_dependencies:
                        graph.stdlib_dependencies[source] = []
                    if target not in graph.stdlib_dependencies[source]:
                        graph.stdlib_dependencies[source].append(target)

            # Detect circular dependencies
            graph.circular_dependencies = self._detect_circular_dependencies(
                graph.internal_dependencies
            )

            # Calculate dependency depths
            graph.dependency_depth = self._calculate_dependency_depth(
                graph.internal_dependencies
            )

            # Calculate statistics
            result.statistics = self._calculate_statistics(result)

            # Add warnings for circular dependencies
            if graph.circular_dependencies:
                for cycle in graph.circular_dependencies:
                    cycle_str = ' -> '.join(cycle)
                    result.warnings.append(f"Circular dependency detected: {cycle_str}")

        except Exception as e:
            error_msg = f"Dependency analysis failed: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        return result

    def _calculate_statistics(self, result: DependencyAnalysisResult) -> Dict[str, Union[int, float]]:
        """Calculate summary statistics from dependency analysis.

        Args:
            result: DependencyAnalysisResult object

        Returns:
            Dictionary of statistics
        """
        graph = result.dependency_graph

        stats = {
            'total_dependencies': len(result.all_dependencies),
            'internal_dependencies': len([d for d in result.all_dependencies if d.dependency_type == 'internal']),
            'external_dependencies': len([d for d in result.all_dependencies if d.dependency_type == 'external']),
            'stdlib_dependencies': len([d for d in result.all_dependencies if d.dependency_type == 'stdlib']),
            'unique_external_modules': len(graph.all_external_modules),
            'unique_internal_modules': len(graph.all_internal_modules),
            'circular_dependency_count': len(graph.circular_dependencies),
            'max_dependency_depth': max(graph.dependency_depth.values()) if graph.dependency_depth else 0,
            'avg_dependency_depth': sum(graph.dependency_depth.values()) / len(graph.dependency_depth) if graph.dependency_depth else 0.0
        }

        # Calculate fan-in and fan-out statistics
        fan_out = [len(deps) for deps in graph.internal_dependencies.values()]
        fan_in = {}

        for source, deps in graph.internal_dependencies.items():
            for dep in deps:
                fan_in[dep] = fan_in.get(dep, 0) + 1

        if fan_out:
            stats['max_fan_out'] = max(fan_out)
            stats['avg_fan_out'] = sum(fan_out) / len(fan_out)
        else:
            stats['max_fan_out'] = 0
            stats['avg_fan_out'] = 0.0

        if fan_in:
            stats['max_fan_in'] = max(fan_in.values())
            stats['avg_fan_in'] = sum(fan_in.values()) / len(fan_in)
        else:
            stats['max_fan_in'] = 0
            stats['avg_fan_in'] = 0.0

        return stats


def main():
    """Main entry point for testing dependency analysis."""
    # This would typically be called from the main analyzer
    print("Dependency analyzer module loaded successfully")


if __name__ == "__main__":
    main()
