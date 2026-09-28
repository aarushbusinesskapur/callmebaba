import sys

def test_python_version():
    """Ensure tests are running in Python 3.10+"""
    assert sys.version_info >= (3, 10), "Python version must be at least 3.10"

def test_project_structure(tmp_path):
    """A minimal placeholder test"""
    assert True
