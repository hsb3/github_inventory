# Development Notes Scratchpad

## tools used

### **Python Built-ins & Core Tools**
- **ast** - Python AST parser
  - *Value:* Zero dependencies, reliable parsing, access to all code structure
  - *Limitations:* Python-only, no semantic analysis, requires manual traversal
- **subprocess** - External tool execution
  - *Value:* Leverage any CLI tool, combine multiple analyses
  - *Limitations:* Reliability depends on external tools, error handling complexity

### **Documentation & Analysis**
- **pydoc** - Python documentation generator
  - *Value:* Built-in, works with any Python code, generates HTML
  - *Limitations:* Basic output, requires importable modules, no customization
- **griffe** - Documentation extraction tool
  - *Value:* Pure AST analysis, rich metadata extraction, JSON output
  - *Limitations:* Installation issues, complex API, fails on import errors
- **pdoc** - Modern documentation generator
  - *Value:* Clean output, minimal config, supports markdown
  - *Limitations:* External dependency, environment sensitivity

### **Code Quality & Metrics**
- **radon** - Complexity metrics
  - *Value:* Multiple metrics (cyclomatic, maintainability, Halstead), JSON output
  - *Limitations:* Limited to complexity, no semantic understanding
- **prospector** - Aggregated static analysis
  - *Value:* 12 tools in one command (Pylint, Bandit, Mypy, etc.), comprehensive
  - *Limitations:* Heavy dependencies, slow, environment-sensitive
- **tokei** - Code statistics
  - *Value:* Fast line counting, language detection, multiple output formats
  - *Limitations:* Surface metrics only, no semantic analysis

### **Visualization & Diagrams**
- **pyreverse** - UML diagram generator
  - *Value:* Class diagrams, package diagrams, inheritance visualization
  - *Limitations:* Requires Graphviz, PNG output only, basic styling
- **ctags** - Code indexing
  - *Value:* Fast symbol extraction, editor integration, language-agnostic
  - *Limitations:* Text-based output, no relationships, limited metadata

### **Search & Navigation**
- **ripgrep** - Fast search tool
  - *Value:* Extremely fast text search, regex support, respects .gitignore
  - *Limitations:* Text search only, no semantic understanding
- **eza** - Enhanced ls replacement
  - *Value:* Better file listing, git integration, tree views
  - *Limitations:* Display tool only, no analysis capabilities

### **Language-Agnostic Parsing**
- **tree_sitter_python** - Universal parser
  - *Value:* Language-agnostic, incremental parsing, error recovery
  - *Limitations:* Complex setup, incorrect metrics in testing, verbose output

### **Development & Testing**
- **pytest** (dry run) - Test discovery
  - *Value:* Test structure analysis without execution, framework detection
  - *Limitations:* Requires valid Python environment, test-focused only
- **git cli** - Version control analysis
  - *Value:* Commit history, contributor analysis, change patterns
  - *Limitations:* Repository-dependent, no code structure insight
- **github cli** - Repository metadata
  - *Value:* Issues, PRs, repository statistics, API access
  - *Limitations:* GitHub-specific, no code analysis

### **Additional Tools Discovered**
- **madge** - JavaScript dependency visualization
  - *Value:* Circular dependency detection, visual graphs, minimal setup
  - *Limitations:* JavaScript/TypeScript only
- **typedoc** - TypeScript documentation generator
  - *Value:* Rich TypeScript documentation, plugin ecosystem
  - *Limitations:* TypeScript-specific, complex configuration
- **pipdeptree** - Python dependency analysis
  - *Value:* Dependency trees, conflict detection, JSON output
  - *Limitations:* Requires installed packages, no code analysis
- **mkdocs + mkdocstrings** - Documentation site generator
  - *Value:* Beautiful documentation sites, auto API docs from docstrings
  - *Limitations:* Configuration overhead, requires docstrings

## key learnings

### **Optimization Breakthrough**
- **Working Optimal Analyzer (67 lines)** achieved 8.3x efficiency over 200+ line approach
- **Quality-to-effort sweet spot** exists around 50-70 lines of analysis code
- **Pure stdlib solutions** consistently outperformed external tool solutions

### **Reliability Hierarchy**
1. **Python AST** - 100% reliable, works everywhere
2. **Subprocess + reliable tools** - Good if tools are available
3. **External PyPI tools** - Failed completely in testing environment
4. **Tree-sitter** - Promising but incorrect metrics in practice

### **Report Quality Insights**
- **Context beats completeness** - production vs test split more valuable than exhaustive lists
- **Framework patterns** (@decorators, async functions) reveal architecture
- **Documentation coverage** indicates codebase maturity
- **4KB reports** provide adequate comprehensive understanding vs 10+ page complexity

### **Failed Approaches**
- **pdoc/griffe** - Installation and import failures despite research promise
- **Tree-sitter** - Severely undercounted lines (8K vs 88K actual for FastAPI)
- **Complex external tool chains** - Unreliable in real environments

## project contents

### folder: /Users/henry/Developer/_sandbox/github_inventory/python_quicklook/adhoc

- initial tests of: ctags, pydoc, pyreverse, rpgrep


### folder: /Users/henry/Developer/_sandbox/github_inventory/python_quicklook/tests

- tests set up for various approaches

### folder: /Users/henry/Developer/_sandbox/github_inventory/python_quicklook/tests/src

- target module to use for local testing

### folder: /Users/henry/Developer/_sandbox/github_inventory/python_quicklook/src

- previous package/module attempt to coordinate various methods
- excluding challenge/ subdirectory

### folder: /Users/henry/Developer/_sandbox/github_inventory/python_quicklook/src/challenge

- relocated scripts from our "challenge" to find the best approaches


---

- pylint (https://pylint.readthedocs.io/en/latest/)
  - pyreverse
  - symilar

- pyclbr
