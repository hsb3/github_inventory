#!/usr/bin/env python3
"""
Directory-wide analysis using the AST prototype (most reliable)
Demonstrates analyzing multiple files to understand codebase structure
"""

import ast
import sys
from pathlib import Path
from collections import defaultdict

def analyze_file_ast(file_path: Path) -> dict:
    """Extract structure from a single Python file using AST."""
    try:
        with open(file_path, 'r') as f:
            source = f.read()
        tree = ast.parse(source)

        result = {
            'imports': [],
            'classes': [],
            'functions': [],
            'file_size': len(source.splitlines())
        }

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    result['imports'].extend([alias.name for alias in node.names])
                else:
                    module = node.module or ''
                    names = [alias.name for alias in node.names]
                    result['imports'].append(f"{module}.{', '.join(names)}")
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                result['classes'].append({'name': node.name, 'methods': methods})
            elif isinstance(node, ast.FunctionDef):
                result['functions'].append(node.name)

        return result
    except:
        return {'imports': [], 'classes': [], 'functions': [], 'file_size': 0}

def analyze_directory(directory: str):
    """Analyze all Python files in a directory."""
    dir_path = Path(directory)
    py_files = list(dir_path.glob("**/*.py"))

    print(f"=== Directory Analysis: {directory} ===")
    print(f"Found {len(py_files)} Python files")
    print()

    all_imports = defaultdict(int)
    all_classes = []
    all_functions = []
    total_lines = 0

    for py_file in py_files:
        if py_file.name.startswith('.'): continue  # Skip hidden files

        analysis = analyze_file_ast(py_file)
        total_lines += analysis['file_size']

        # Aggregate data
        for imp in analysis['imports']:
            all_imports[imp.split('.')[0]] += 1
        all_classes.extend([cls['name'] for cls in analysis['classes']])
        all_functions.extend(analysis['functions'])

        # Show file summary
        if analysis['classes'] or analysis['functions']:
            print(f"📄 {py_file.name} ({analysis['file_size']} lines)")
            for cls in analysis['classes'][:2]:  # Limit output
                methods_str = f" ({len(cls['methods'])} methods)" if cls['methods'] else ""
                print(f"   🏛️  {cls['name']}{methods_str}")
            for func in analysis['functions'][:3]:  # Limit output
                print(f"   ⚙️  {func}()")
            print()

    # Summary
    print("=== CODEBASE SUMMARY ===")
    print(f"📊 Total lines: {total_lines}")
    print(f"🏛️  Classes: {len(set(all_classes))}")
    print(f"⚙️  Functions: {len(set(all_functions))}")

    # Most used imports
    top_imports = sorted(all_imports.items(), key=lambda x: x[1], reverse=True)[:5]
    if top_imports:
        imports_str = ', '.join([f"{imp}({count})" for imp, count in top_imports])
        print(f"📦 Key imports: {imports_str}")

if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else "../src/github_inventory"
    analyze_directory(directory)
