#!/usr/bin/env python3
"""
Prototype 1: Quick codebase understanding using griffe (PyPI tool)
Under 30 lines - extracts classes, functions, and their relationships
"""

import sys
from pathlib import Path

try:
    from griffe import load
except ImportError:
    print("Install griffe: pip install griffe")
    sys.exit(1)


def analyze_codebase_griffe(module_path: str) -> None:
    """Analyze Python codebase using griffe for quick understanding."""
    try:
        import tempfile, shutil, sys

        module_name = Path(module_path).stem
        temp_dir = tempfile.mkdtemp()
        temp_file = Path(temp_dir) / f"{module_name}.py"
        shutil.copy2(module_path, temp_file)
        sys.path.insert(0, temp_dir)

        print(f"=== Griffe Analysis: {module_name} ===")

        # Simple griffe loading
        package = load(module_name)

        # Extract classes and methods
        for class_name, cls in package.classes.items():
            print(f"🏛️  Class: {class_name}")
            if hasattr(cls, 'docstring') and cls.docstring:
                doc_text = cls.docstring.value if hasattr(cls.docstring, 'value') else str(cls.docstring)
                print(f"   📄 {doc_text.split('.')[0]}")
            methods = list(cls.methods.keys())[:4] if hasattr(cls, 'methods') else []
            for method_name in methods:
                print(f"   🔧 {method_name}()")

        # Extract standalone functions
        functions = list(package.functions.keys())[:6] if hasattr(package, 'functions') else []
        for func_name in functions:
            print(f"⚙️  Function: {func_name}()")

        sys.path.remove(temp_dir)
        shutil.rmtree(temp_dir)

    except Exception as e:
        print(f"=== Griffe Fallback Analysis: {Path(module_path).name} ===")
        # Simple regex-based fallback
        with open(module_path) as f:
            content = f.read()
            import re
            classes = re.findall(r'^class (\w+)', content, re.MULTILINE)
            functions = re.findall(r'^def (\w+)', content, re.MULTILINE)
            imports = re.findall(r'^(?:from \S+ )?import (.+)', content, re.MULTILINE)

            if imports: print(f"📦 Imports: {', '.join(imports[:3])}...")
            for cls in classes: print(f"🏛️  Class: {cls}")
            for func in functions: print(f"⚙️  Function: {func}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python prototype_1_griffe.py <python_file>")
        sys.exit(1)
    analyze_codebase_griffe(sys.argv[1])
