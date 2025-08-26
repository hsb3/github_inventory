#!/bin/bash

echo "Testing pydoc method for code analysis..."
cd ../../src

echo "Generating HTML documentation for all modules..."
python -m pydoc -w github_inventory

echo "Generating text documentation and extracting structure..."
{
    echo "# Code Structure Analysis - PyDoc Method"
    echo "Generated on: $(date)"
    echo ""

    # Get module structure
    for module in github_inventory/*.py; do
        if [[ -f "$module" && "$(basename "$module")" != "__init__.py" ]]; then
            module_name=$(basename "$module" .py)
            echo "## Module: github_inventory.$module_name"
            python -c "
import github_inventory.$module_name
import inspect
import sys

module = sys.modules['github_inventory.$module_name']

print('### Classes:')
for name, obj in inspect.getmembers(module, inspect.isclass):
    if obj.__module__ == 'github_inventory.$module_name':
        print(f'- **{name}**')
        for method_name, method in inspect.getmembers(obj, inspect.ismethod):
            print(f'  - {method_name}()')
        for func_name, func in inspect.getmembers(obj, inspect.isfunction):
            print(f'  - {func_name}()')

print()
print('### Functions:')
for name, obj in inspect.getmembers(module, inspect.isfunction):
    if obj.__module__ == 'github_inventory.$module_name':
        sig = inspect.signature(obj)
        print(f'- **{name}**{sig}')
print()
" 2>/dev/null || echo "Error analyzing $module_name"
        fi
    done
} > ../code_analysis_tests/pydoc/output.md

echo "Moving HTML files to pydoc directory..."
mv *.html ../code_analysis_tests/pydoc/ 2>/dev/null || true

echo "PyDoc analysis complete. Check output.md and HTML files."
