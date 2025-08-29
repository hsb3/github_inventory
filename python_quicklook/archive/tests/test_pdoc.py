#!/usr/bin/env python3
"""Test pdoc solution for codebase analysis."""

import sys
import subprocess
import tempfile
from pathlib import Path

def analyze_with_pdoc(target_path):
    """Analyze codebase using pdoc."""
    print(f"=== PDOC ANALYSIS: {Path(target_path).name} ===")

    # Try to extract module info using pdoc's internal API
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run([
                'pdoc', '--no-show-source', '--output-directory', tmpdir, target_path
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                # Count generated HTML files
                html_files = list(Path(tmpdir).glob("**/*.html"))
                print(f"📊 Generated documentation for {len(html_files)} modules")
                print(f"🏛️  Modules: {', '.join([f.stem for f in html_files[:10]])}")
            else:
                print(f"❌ Failed: {result.stderr[:200]}...")

    except Exception as e:
        print(f"❌ Error: {str(e)[:100]}...")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_pdoc.py <directory>")
        sys.exit(1)
    analyze_with_pdoc(sys.argv[1])
