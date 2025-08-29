#!/usr/bin/env python3
"""
Test all three prototypes on the same codebase for comparison
"""

import sys
import subprocess
from pathlib import Path

def test_prototype(script_name: str, target_file: str) -> None:
    """Test a prototype script and capture output."""
    try:
        result = subprocess.run(
            [sys.executable, script_name, target_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        print(result.stdout)
        if result.stderr:
            print(f"Stderr: {result.stderr}")
    except subprocess.TimeoutExpired:
        print(f"❌ {script_name} timed out")
    except Exception as e:
        print(f"❌ {script_name} failed: {e}")
    print("-" * 60)

def main():
    target_file = "../src/github_inventory/cli.py"  # Real codebase file

    print("=" * 60)
    print("PROTOTYPE COMPARISON: CLI.PY ANALYSIS")
    print("=" * 60)

    # Test all three prototypes
    test_prototype("prototype_1_griffe.py", target_file)
    test_prototype("prototype_2_treesitter.py", target_file)
    test_prototype("prototype_3_ast.py", target_file)

if __name__ == "__main__":
    main()
