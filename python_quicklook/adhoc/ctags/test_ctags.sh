#!/bin/bash

echo "Testing ctags method for code analysis..."
cd ../../

echo "Checking if ctags is installed..."
if ! command -v ctags &> /dev/null; then
    echo "Installing ctags..."
    if command -v brew &> /dev/null; then
        brew install ctags
    elif command -v apt-get &> /dev/null; then
        sudo apt-get install -y ctags
    else
        echo "Please install ctags manually and run this script again"
        exit 1
    fi
fi

echo "Generating ctags file..."
ctags -R --languages=python --python-kinds=-i src/github_inventory/

echo "Converting ctags to markdown format..."
{
    echo "# Code Structure Analysis - CTags Method"
    echo "Generated on: $(date)"
    echo ""

    if [[ -f "tags" ]]; then
        echo "## Classes"
        grep -E "^[[:alpha:]_][[:alnum:]_]*[[:space:]].*[[:space:]]c[[:space:]]" tags | awk '{print "- " $1}' | sort -u
        echo ""

        echo "## Functions/Methods"
        grep -E "^[[:alpha:]_][[:alnum:]_]*[[:space:]].*[[:space:]]f[[:space:]]" tags | awk '{print "- " $1 " (" $2 ")"}' | sort
        echo ""

        echo "## All Symbols Summary"
        echo "| Symbol | Type | File |"
        echo "|--------|------|------|"

        while IFS=$'\t' read -r symbol file pattern type; do
            case "$type" in
                "c") type_name="Class" ;;
                "f") type_name="Function" ;;
                "m") type_name="Method" ;;
                *) type_name="Other" ;;
            esac
            echo "| $symbol | $type_name | $file |"
        done < tags | head -50  # Limit to first 50 for readability

        mv tags code_analysis_tests/ctags/
    else
        echo "Error: tags file not generated"
    fi
} > code_analysis_tests/ctags/output.md

echo "CTags analysis complete. Check output.md and tags file."
