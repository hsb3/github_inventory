#!/usr/bin/env python3
"""Test griffe solution for codebase analysis."""

import sys
from pathlib import Path

def analyze_with_griffe(target_path):
    """Analyze codebase using griffe."""
    print(f"=== GRIFFE ANALYSIS: {Path(target_path).name} ===")

    try:
        from griffe import load_package
        from griffe.loader import GriffeLoader

        # Try to load as package
        loader = GriffeLoader()
        py_files = list(Path(target_path).glob("**/*.py"))
        modules_found = 0
        classes_found = []
        functions_found = []

        for py_file in py_files[:20]:  # Limit to avoid timeout
            try:
                module_name = py_file.stem
                if module_name != '__init__':
                    package = loader.load_module(module_name, filepath=py_file)
                    modules_found += 1

                    # Extract classes and functions
                    for member_name, member in package.members.items():
                        if hasattr(member, 'kind'):
                            if member.kind.value == 'class':
                                method_count = len([m for m in member.members.values() if hasattr(m, 'kind') and m.kind.value == 'function'])
                                classes_found.append(f"{member_name}({method_count} methods)")
                            elif member.kind.value == 'function':
                                functions_found.append(member_name)

            except Exception:
                continue

        print(f"📊 Analyzed {modules_found} modules from {len(py_files)} files")
        if classes_found: print(f"🏛️  Classes: {', '.join(classes_found[:8])}")
        if functions_found: print(f"⚙️  Functions: {', '.join(functions_found[:10])}")

    except Exception as e:
        print(f"❌ Error: {str(e)[:100]}...")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_griffe.py <directory>")
        sys.exit(1)
    analyze_with_griffe(sys.argv[1])
