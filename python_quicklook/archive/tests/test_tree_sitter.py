#!/usr/bin/env python3
"""Test tree-sitter solution for codebase analysis."""

import sys
from pathlib import Path

def analyze_with_tree_sitter(target_path):
    """Analyze codebase using tree-sitter."""
    print(f"=== TREE-SITTER ANALYSIS: {Path(target_path).name} ===")

    try:
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser

        PY_LANGUAGE = Language(tspython.language())
        parser = Parser(PY_LANGUAGE)

        py_files = list(Path(target_path).glob("**/*.py"))
        imports_found = set()
        classes_found = []
        functions_found = []
        total_lines = 0

        for py_file in py_files[:50]:  # Limit for performance
            try:
                source_code = py_file.read_text(encoding='utf-8')
                total_lines += len(source_code.splitlines())
                tree = parser.parse(bytes(source_code, "utf8"))

                def traverse_tree(node):
                    if node.type == 'import_statement':
                        for child in node.children:
                            if child.type == 'dotted_name':
                                imports_found.add(child.text.decode('utf-8').split('.')[0])
                    elif node.type == 'import_from_statement':
                        for child in node.children:
                            if child.type == 'dotted_name':
                                imports_found.add(child.text.decode('utf-8').split('.')[0])
                    elif node.type == 'class_definition':
                        class_name = None
                        method_count = 0
                        for child in node.children:
                            if child.type == 'identifier':
                                class_name = child.text.decode('utf-8')
                            elif child.type == 'block':
                                method_count = len([c for c in child.children if c.type == 'function_definition'])
                        if class_name:
                            classes_found.append(f"{class_name}({method_count} methods)")
                    elif node.type == 'function_definition':
                        for child in node.children:
                            if child.type == 'identifier':
                                functions_found.append(child.text.decode('utf-8'))
                                break

                    for child in node.children:
                        traverse_tree(child)

                traverse_tree(tree.root_node)

            except Exception:
                continue

        print(f"📊 {len(py_files)} files, {total_lines} lines")
        top_imports = sorted(imports_found)[:8]
        if top_imports: print(f"📦 Key imports: {', '.join(top_imports)}")
        if classes_found: print(f"🏛️  Classes: {', '.join(classes_found[:8])}")
        if functions_found: print(f"⚙️  Functions: {', '.join(functions_found[:10])}")

    except Exception as e:
        print(f"❌ Error: {str(e)[:100]}...")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_tree_sitter.py <directory>")
        sys.exit(1)
    analyze_with_tree_sitter(sys.argv[1])
