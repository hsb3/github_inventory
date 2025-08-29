# 🚀 Next Iteration Plan - REPORT_MOCKUP Implementation

**Objective:** Build tool matching REPORT_MOCKUP.md specification in <50 lines
**Target:** 5-10 page comprehensive reports using optimal tool leverage

---

## 📋 Required Report Sections (from REPORT_MOCKUP.md)

1. **README excerpt + GitHub link** (first ~150 lines)
2. **Package/module/class/function counts** (excluding main() in __init__.py)
3. **All classes with docstrings** (complete inventory)
4. **Rank-ordered method list** (by occurrence count, excluding tests)
5. **External dependencies** (complete list)
6. **Code coverage summary** (if available)
7. **Class DAG** (input/output relationships)

---

## 🔧 Tools Needed for Each Section

### **1. README Extraction**
- **GitHub CLI**: `gh api repos/{owner}/{repo}/readme` (if GitHub repo)
- **File reading**: Direct file read for local projects
- **Target**: First 150 lines + GitHub link

### **2. Code Structure Counts**
- **AST analysis**: Count packages (__init__.py), modules, classes, functions
- **Exclusions**: main() in __init__.py/__main__.py files
- **From scavenge**: `working_optimal_analyzer.py` has this logic

### **3. Class Inventory with Docstrings**
- **AST traversal**: `ast.get_docstring()` for each class
- **From scavenge**: `hybrid_analyzer.py` has docstring extraction

### **4. Method Ranking by Occurrence** ⭐ **NEW REQUIREMENT**
- **AST + text search**: Count method calls across codebase
- **Exclusion**: Ignore test files (tests/, test_*.py)
- **Challenge**: Need to build this analyzer

### **5. External Dependencies**
- **Multiple sources**: pyproject.toml, requirements.txt, setup.py, imports
- **From scavenge**: Existing import analysis in prototypes

### **6. Code Coverage** ⭐ **NEW REQUIREMENT**
- **pytest --collect-only**: Test discovery without execution
- **coverage.py**: If .coverage file exists
- **Challenge**: Optional feature

### **7. Class DAG** ⭐ **COMPLEX NEW REQUIREMENT**
- **Function/method signature analysis**: Parse input/output types
- **Dependency mapping**: Which classes use which other classes
- **Challenge**: Most complex requirement

---

## 💡 Optimal Implementation Strategy

### **Phase 1: Core Analysis (30 lines)**
```python
# Leverage existing working_optimal_analyzer.py as base
# Add: README extraction, method occurrence counting
# Output: Raw data for report generation
```

### **Phase 2: Advanced Analysis (15 lines)**
```python
# Add: Class DAG generation, coverage detection
# Use: networkx for graph analysis if available
# Fallback: Simple relationship mapping
```

### **Phase 3: Report Assembly (5 lines)**
```python
# Combine all data into REPORT_MOCKUP format
# Use: Specialized agent for final formatting
# Output: 5-10 page markdown report
```

---

## 🎯 Technical Approach

### **Method Occurrence Ranking Algorithm:**
1. Parse all non-test Python files with AST
2. Find all `ast.Call` nodes where `func.attr` is a method name
3. Count occurrences across codebase
4. Rank by frequency

### **Class DAG Generation:**
1. Analyze function signatures for type hints
2. Track class instantiations and method calls
3. Map which classes depend on which other classes
4. Generate simple text-based or mermaid DAG

### **Tool Selection Priority:**
1. **Python AST** - Core analysis (reliable, fast)
2. **GitHub CLI** - README/repo metadata (if available)
3. **subprocess** - Leverage coverage.py, other tools (optional)
4. **Specialized agent** - Final report assembly

---

## 🔄 Migration from Challenge Results

### **Scavenge Folder Contents:**
- `working_optimal_analyzer.py` - **BASE** for core structure analysis
- `hybrid_analyzer.py` - **SOURCE** for docstring extraction
- `quick_analyze.py` - **REFERENCE** for ultra-compact approach
- Other prototypes - **BACKUP** solutions

### **Archive Folder:**
- `src/` - Original comprehensive implementation
- `tests/` - Test suite for reference

---

## ✅ Next Steps

1. **Build core analyzer** (30 lines) using best parts from scavenge/
2. **Add method ranking algorithm** (new requirement)
3. **Implement class DAG generation** (most complex part)
4. **Create report assembly** using specialized agent
5. **Test on FastAPI/Requests** to verify 5-10 page output quality

**Success Criteria:** Generate reports matching REPORT_MOCKUP.md sections in <50 lines total.
