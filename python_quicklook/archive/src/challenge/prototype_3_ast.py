#!/usr/bin/env python3
"""
Prototype 3: Quick codebase understanding using Python's built-in AST
Under 30 lines - zero dependencies, extracts core structure and relationships
"""

import ast
import sys
from pathlib import Path
from typing import List


def analyze_codebase_ast(file_path: str) -> None:
    """Analyze Python codebase using built-in AST for quick understanding."""
    try:
        with open(file_path, 'r') as f:
            source = f.read()

        tree = ast.parse(source)
        print(f"=== AST Analysis: {Path(file_path).name} ===")

        imports = []
        classes = []
        functions = []

        # First pass: collect top-level items
        for node in tree.body:
            if isinstance(node, ast.Import):
                imports.extend([alias.name for alias in node.names])
            elif isinstance(node, ast.ImportFrom):
                imports.append(f"{node.module or ''}.{', '.join([a.name for a in node.names])}")
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                bases = [b.id if hasattr(b, 'id') else str(b) for b in node.bases]
                classes.append((node.name, methods, bases))
            elif isinstance(node, ast.FunctionDef):
                params = [arg.arg for arg in node.args.args]
                functions.append((node.name, params))

        # Display results
        if imports: print(f"📦 Imports: {', '.join(imports[:5])}{'...' if len(imports) > 5 else ''}")

        for name, methods, bases in classes:
            base_str = f" -> {', '.join(bases)}" if bases else ""
            print(f"🏛️  Class: {name}{base_str}")
            for method in methods[:3]:  # Show first 3 methods
                print(f"   🔧 {method}()")

        for name, params in functions:
            param_str = f"({', '.join(params[:3])}{'...' if len(params) > 3 else ''})"
            print(f"⚙️  Function: {name}{param_str}")

    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python prototype_3_ast.py <python_file>")
        sys.exit(1)
    analyze_codebase_ast(sys.argv[1])
