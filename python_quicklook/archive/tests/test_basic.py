"""
Basic tests for Python Quick Look tool
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.python_quicklook import PythonQuickLook


def test_python_quicklook_init():
    """Test basic initialization"""
    analyzer = PythonQuickLook(".")
    assert analyzer.target_dir == Path(".")
    assert analyzer.modules == []


def test_should_ignore():
    """Test ignore pattern functionality"""
    analyzer = PythonQuickLook(".")

    # Should ignore common patterns
    assert analyzer.should_ignore(Path("__pycache__/test.py"))
    assert analyzer.should_ignore(Path(".git/config"))
    assert analyzer.should_ignore(Path("node_modules/package"))
    assert analyzer.should_ignore(Path(".hidden_file"))

    # Should not ignore regular Python files
    assert not analyzer.should_ignore(Path("test.py"))
    assert not analyzer.should_ignore(Path("src/module.py"))
