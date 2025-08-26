


## scratchpad

**sections**

- first ~150 lines of readme and link to file on github
- number of packages, modules (count __init__.py), classes and functions (excluding main() in __init__.py or __main__.py files)
- list of all classes with top-level docstring
- rank-ordered list of class methods; ranking by counting number of occurrences in code base (excluding tests/* , test_*.py)
- external dependencies list
- code coverage summary stats
- class DAG (based on input/output of functions and class methods)


**methodology**

- use pre-built tools built-in, from pypi, from npm to assemble raw informatoin needed to assemble report
- create/execute any lightweight additional utilities needed for additional information
- pass above information to specialized agent(s) to create final report
