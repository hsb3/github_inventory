#!/bin/bash

echo "Testing pyreverse method for code analysis..."
cd ../../

echo "Checking if pylint is installed (needed for pyreverse)..."
if ! command -v pyreverse &> /dev/null; then
    echo "Installing pylint for pyreverse..."
    uv add pylint
fi

echo "Generating class diagram with pyreverse..."
pyreverse -o png -p github_inventory src/github_inventory/

echo "Generating text-based class list..."
{
    echo "# Code Structure Analysis - PyReverse Method"
    echo "Generated on: $(date)"
    echo ""

    # Use pyreverse to get class information and format as markdown
    echo "## Class and Function Analysis"
    echo ""

    # Run pyreverse to get detailed info
    pyreverse -f ALL -o txt -p github_inventory src/github_inventory/ 2>/dev/null || true

    # Parse the generated files for a cleaner output
    if [[ -f "classes_github_inventory.txt" ]]; then
        echo "### Classes found:"
        cat classes_github_inventory.txt | grep -E "^class|^def" | sed 's/^/- /'
        echo ""
        rm classes_github_inventory.txt packages_github_inventory.txt 2>/dev/null || true
    fi

    # Alternative method using Python AST parsing
    python3 -c "
import ast
import os

def analyze_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read())
        except:
            return [], []

    classes = []
    functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            classes.append((node.name, methods))
        elif isinstance(node, ast.FunctionDef) and not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree) if hasattr(parent, 'body') and node in getattr(parent, 'body', [])):
            functions.append(node.name)

    return classes, functions

print('### Detailed Analysis:')
for root, dirs, files in os.walk('src/github_inventory'):
    for file in files:
        if file.endswith('.py') and file != '__init__.py':
            filepath = os.path.join(root, file)
            module_name = file[:-3]
            classes, functions = analyze_file(filepath)

            print(f'\\n#### Module: {module_name}')
            if classes:
                print('**Classes:**')
                for class_name, methods in classes:
                    print(f'- {class_name}')
                    for method in methods:
                        print(f'  - {method}()')

            if functions:
                print('**Functions:**')
                for func in functions:
                    print(f'- {func}()')
"
} > code_analysis_tests/pyreverse/output.md

echo "Moving PNG files to pyreverse directory..."
mv *.png code_analysis_tests/pyreverse/ 2>/dev/null || true

echo "PyReverse analysis complete. Check output.md and PNG files."
