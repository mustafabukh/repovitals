"""Analyze the health of Git repositories and Python dependencies."""

from repovitals.git_history import load_history

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "load_history",
]
