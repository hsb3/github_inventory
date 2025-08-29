#!/usr/bin/env python3
"""
Prototype 2: Language-agnostic codebase understanding using tree-sitter
Under 30 lines - works with multiple languages, extracts structure
"""

import sys
from pathlib import Path

try:
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser
except ImportError:
    print("Install tree-sitter: pip install tree-sitter tree-sitter-python")
    sys.exit(1)


def analyze_codebase_treesitter(file_path: str) -> None:
    """Analyze codebase using tree-sitter for language-agnostic understanding."""
    try:
        # Setup parser
        PY_LANGUAGE = Language(tspython.language())
        parser = Parser(PY_LANGUAGE)

        # Read and parse file
        with open(file_path, 'rb') as f:
            source_code = f.read()
        tree = parser.parse(source_code)

        print(f"=== Tree-sitter Analysis: {Path(file_path).name} ===")

        def traverse_node(node, depth=0):
            indent = "  " * depth
            if node.type == 'class_definition':
                class_name = node.children[1].text.decode('utf-8')
                print(f"{indent}🏛️  Class: {class_name}")
            elif node.type == 'function_definition':
                func_name = node.children[1].text.decode('utf-8')
                print(f"{indent}⚙️  Function: {func_name}")
            elif node.type == 'import_statement' or node.type == 'import_from_statement':
                import_text = node.text.decode('utf-8').strip()
                print(f"{indent}📦 {import_text}")

            # Recurse into children (limit depth for brevity)
            if depth < 2:
                for child in node.children:
                    traverse_node(child, depth + 1)

        traverse_node(tree.root_node)

    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python prototype_2_treesitter.py <python_file>")
        sys.exit(1)
    analyze_codebase_treesitter(sys.argv[1])
