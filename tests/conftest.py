"""Test fixtures for git-evolve tests."""
import os
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_repo_root():
    """Provide a mock repository root path."""
    return "/home/user/test-repo"


@pytest.fixture
def mock_porcelain_output():
    """Provide sample porcelain blame output."""
    return """abc12345678901234567890123456789012 author 2024-01-01 +0000	1
	def hello():
abc12345678901234567890123456789012 author 2024-01-01 +0000	2
	    return "hello"
def45678901234567890123456789012345 author 2024-01-02 +0000	3
		def world():
abc12345678901234567890123456789012 author 2024-01-01 +0000	4
		    return "world"
"""


@pytest.fixture
def sample_analysis_result():
    """Provide sample analysis result dictionary."""
    return {
        "base_commit": "abc12345678901234567890123456789012",
        "total_lines": 1000,
        "base_lines_surviving": 700,
        "manual_or_modified_lines": 300,
        "evolution_percent": 30.0,
        "survival_percent": 70.0,
        "files_analyzed": 10,
        "repository": "test-repo",
        "file_breakdown": [
            {"file": "src/main.py", "total_lines": 200, "evolved_lines": 100, "evolution_percent": 50.0},
            {"file": "src/utils.py", "total_lines": 100, "evolved_lines": 80, "evolution_percent": 80.0},
            {"file": "src/config.py", "total_lines": 50, "evolved_lines": 10, "evolution_percent": 20.0},
        ]
    }


@pytest.fixture
def mock_git_command():
    """Provide a mock for run_git_command."""
    with MagicMock() as mock:
        yield mock
