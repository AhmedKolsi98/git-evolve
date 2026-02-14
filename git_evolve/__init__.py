"""git-evolve: Measure code evolution from any base commit.

A Python package and CLI tool for analyzing how much a codebase has evolved
since a specific starting point using git blame statistics.

Example:
    >>> from git_evolve import analyze
    >>> result = analyze('v1.0.0')
    >>> print(f"Evolution: {result['evolution_percent']}%")
"""
__version__ = "0.2.0"
__author__ = "Ahmed Kolsi"
__all__ = ["analyze"]

from .analyzer import analyze
