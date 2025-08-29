#!/usr/bin/env python3
"""Ultra-compact Python codebase analyzer - provides quick functional understanding."""

import ast
import sys
from collections import defaultdict
from pathlib import Path


def analyze_python_code(target):
    """Analyze Python code structure and provide quick functional overview."""
    files = (
        [Path(target)] if Path(target).is_file() else list(Path(target).glob("**/*.py"))
    )
    imports, classes, functions, total_lines = defaultdict(int), [], [], 0

    for f in files:
        try:
            tree = ast.parse(f.read_text())
            total_lines += len(f.read_text().splitlines())
            for node in tree.body:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports[alias.name.split(".")[0]] += 1
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports[node.module.split(".")[0]] += 1
                elif isinstance(node, ast.ClassDef):
                    methods = [
                        n.name for n in node.body if isinstance(n, ast.FunctionDef)
                    ]
                    classes.append(f"{node.name}({len(methods)} methods)")
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
        except:
            pass

    print(f"📊 {len(files)} files, {total_lines} lines")
    if imports:
        print(
            f"📦 Key imports: {', '.join([f'{k}({v})' for k,v in sorted(imports.items(), key=lambda x: x[1], reverse=True)[:5]])}"
        )
    if classes:
        print(f"🏛️  Classes: {', '.join(classes[:8])}")
    if functions:
        print(f"⚙️  Functions: {', '.join(functions[:10])}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_analyze.py <file_or_directory>")
        sys.exit(1)
    analyze_python_code(sys.argv[1])
