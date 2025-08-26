#!/bin/bash

echo "Testing ripgrep method for code analysis..."
cd ../../

echo "Using ripgrep to extract code structure..."
{
    echo "# Code Structure Analysis - Ripgrep Method"
    echo "Generated on: $(date)"
    echo ""

    echo "## Classes"
    rg "^class\s+(\w+)" --type py src/ --only-matching --no-filename --no-line-number | sort -u | sed 's/^/- /'
    echo ""

    echo "## Functions (standalone)"
    rg "^def\s+(\w+)" --type py src/ --only-matching --no-filename --no-line-number | grep -v "^def __" | sort -u | sed 's/^/- /'
    echo ""

    echo "## Methods (indented functions)"
    rg "^\s+def\s+(\w+)" --type py src/ --only-matching --no-filename --no-line-number | sed 's/^[ \t]*//' | sort -u | sed 's/^/- /'
    echo ""

    echo "## Detailed File Analysis"
    for file in $(find src/ -name "*.py" -type f | grep -v __pycache__ | sort); do
        filename=$(basename "$file" .py)
        echo "### Module: $filename"
        echo "**File:** $file"
        echo ""

        echo "**Classes:**"
        rg "^class\s+(\w+).*:" --only-matching "$file" 2>/dev/null | sed 's/^/- /' || echo "- None"
        echo ""

        echo "**Functions:**"
        rg "^def\s+(\w+)\(" --only-matching "$file" 2>/dev/null | sed 's/^/- /' || echo "- None"
        echo ""

        echo "**Methods:**"
        rg "^\s+def\s+(\w+)\(" --only-matching "$file" 2>/dev/null | sed 's/^[ \t]*/- /' || echo "- None"
        echo ""

        # Show imports as well
        echo "**Imports:**"
        rg "^(import|from)\s+" --only-matching "$file" 2>/dev/null | sed 's/^/- /' || echo "- None"
        echo ""
        echo "---"
        echo ""
    done

    echo "## Summary Statistics"
    echo "- **Total Python files:** $(find src/ -name "*.py" -type f | wc -l)"
    echo "- **Total classes:** $(rg "^class\s+\w+" --type py src/ | wc -l)"
    echo "- **Total functions:** $(rg "^def\s+\w+" --type py src/ | wc -l)"
    echo "- **Total methods:** $(rg "^\s+def\s+\w+" --type py src/ | wc -l)"
    echo "- **Total imports:** $(rg "^(import|from)\s+" --type py src/ | wc -l)"

} > code_analysis_tests/ripgrep/output.md

echo "Ripgrep analysis complete. Check output.md file."
