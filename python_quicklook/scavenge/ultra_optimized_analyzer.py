#!/usr/bin/env python3
"""Ultra-optimized analyzer - maximum report quality in <50 lines."""

import subprocess
import json
import sys
from pathlib import Path

def comprehensive_analysis(target):
    """Generate comprehensive report using highest-leverage tools."""
    target_path = Path(target)
    output_dir = Path(f"analysis_{target_path.name}")
    output_dir.mkdir(exist_ok=True)

    print(f"🔍 Comprehensive analysis of {target_path.name}")

    # 1. Prospector: Aggregates 12 static analysis tools in one command
    subprocess.run(["prospector", "--output-format=json", f"--output-file={output_dir}/analysis.json", str(target_path)], capture_output=True)

    # 2. Pyreverse: Generate UML class diagrams
    subprocess.run(["pyreverse", "-o", "png", "-p", target_path.name, "-d", str(output_dir), str(target_path)], capture_output=True)

    # 3. Radon: Comprehensive complexity metrics
    subprocess.run(["radon", "cc", "--json", str(target_path)], stdout=open(output_dir / "complexity.json", "w"), stderr=subprocess.DEVNULL)

    # 4. Generate comprehensive markdown report
    with open(output_dir / "report.md", "w") as f:
        f.write(f"# 📋 {target_path.name} - Comprehensive Analysis\n\n")

        # Include UML diagrams
        for diagram in output_dir.glob("*.png"):
            f.write(f"## 🎨 {diagram.stem.replace('_', ' ').title()}\n![{diagram.stem}]({diagram.name})\n\n")

        # Static analysis summary
        try:
            with open(output_dir / "analysis.json") as analysis_file:
                analysis = json.load(analysis_file)
                if "summary" in analysis:
                    f.write(f"## 📊 Quality Score: {analysis['summary'].get('score', 'N/A')}/10\n\n")
                if "messages" in analysis:
                    f.write(f"### Top Issues ({len(analysis['messages'])} total)\n\n")
                    for msg in analysis["messages"][:15]:
                        f.write(f"- **{msg.get('symbol', 'Issue')}**: {msg.get('message', '')[:100]}...\n")
                    f.write("\n")
        except: pass

        # Complexity analysis
        try:
            with open(output_dir / "complexity.json") as complexity_file:
                complexity = json.load(complexity_file)
                all_funcs = [(f.get('name'), f.get('complexity'), path)
                           for path, funcs in complexity.items() for f in funcs]
                top_complex = sorted(all_funcs, key=lambda x: x[1] or 0, reverse=True)[:10]
                f.write("### 🔥 Most Complex Functions\n\n")
                for name, comp, path in top_complex:
                    f.write(f"- **{name}** (Complexity: {comp}) in {Path(path).name}\n")
        except: pass

    print(f"✅ Complete report: {output_dir}/report.md")
    print(f"📊 Analysis data: {output_dir}/analysis.json")
    print(f"🎨 UML diagrams: {list(output_dir.glob('*.png'))}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python ultra_optimized_analyzer.py <target_directory>")
        sys.exit(1)
    comprehensive_analysis(sys.argv[1])
