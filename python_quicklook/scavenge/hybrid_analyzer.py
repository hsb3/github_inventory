#!/usr/bin/env python3
"""Enhanced hybrid codebase analyzer - combines best insights from all approaches."""

import ast, sys, os, re
from pathlib import Path
from collections import defaultdict, Counter

def analyze_enhanced(target):
    """Enhanced analysis combining multiple insights."""
    files = [Path(target)] if Path(target).is_file() else list(Path(target).glob("**/*.py"))

    # Core metrics
    imports, classes, functions = defaultdict(int), [], []
    total_lines = prod_lines = test_lines = 0

    # Enhanced insights
    decorators, docstring_coverage = Counter(), 0
    async_functions, class_methods = 0, defaultdict(list)

    for f in files:
        try:
            content = f.read_text()
            tree = ast.parse(content)
            lines = len(content.splitlines())
            total_lines += lines

            # Separate production vs test code
            if 'test' in str(f).lower(): test_lines += lines
            else: prod_lines += lines

            for node in tree.body:
                # Enhanced import analysis
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split('.')[0]
                        imports[root] += 1
                elif isinstance(node, ast.ImportFrom) and node.module:
                    root = node.module.split('.')[0]
                    imports[root] += 1

                # Enhanced class analysis
                elif isinstance(node, ast.ClassDef):
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(item.name)
                            if item.decorator_list:
                                for dec in item.decorator_list:
                                    if isinstance(dec, ast.Name):
                                        decorators[dec.id] += 1
                    class_methods[node.name] = methods
                    classes.append(f"{node.name}({len(methods)})")

                # Enhanced function analysis
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                    if node.decorator_list:
                        for dec in node.decorator_list:
                            if isinstance(dec, ast.Name):
                                decorators[dec.id] += 1
                    if any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(node)):
                        async_functions += 1

            # Docstring coverage
            if ast.get_docstring(tree): docstring_coverage += 1

        except: pass

    # Output enhanced results
    is_test_heavy = test_lines > prod_lines
    print(f"📊 {len(files)} files, {total_lines} lines ({prod_lines} prod, {test_lines} test)")

    if imports:
        top_imports = sorted(imports.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"📦 Dependencies: {', '.join([f'{k}({v})' for k,v in top_imports])}")

    if classes:
        print(f"🏛️  Classes: {', '.join(classes[:6])}")

    if functions:
        func_preview = functions[:8]
        if is_test_heavy:
            test_funcs = [f for f in func_preview if 'test' in f.lower()]
            other_funcs = [f for f in func_preview if 'test' not in f.lower()]
            if test_funcs: print(f"🧪 Tests: {', '.join(test_funcs[:4])}")
            if other_funcs: print(f"⚙️  Functions: {', '.join(other_funcs[:4])}")
        else:
            print(f"⚙️  Functions: {', '.join(func_preview)}")

    # Enhanced insights
    if decorators:
        top_decorators = decorators.most_common(3)
        print(f"🎯 Decorators: {', '.join([f'@{k}({v})' for k,v in top_decorators])}")

    coverage_pct = round(100 * docstring_coverage / len(files)) if files else 0
    if coverage_pct > 20: print(f"📝 Docs: {coverage_pct}% files have docstrings")
    if async_functions > 2: print(f"⚡ Async: {async_functions} async functions detected")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python hybrid_analyzer.py <file_or_directory>")
        sys.exit(1)
    analyze_enhanced(sys.argv[1])
