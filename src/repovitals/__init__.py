"""Analyze the health of Git repositories and Python dependencies."""

from repovitals.dependencies import load_dependencies, parse_requirement
from repovitals.git_history import load_history
from repovitals.metrics import summarize_repository
from repovitals.models import (
    ContributorStat,
    DependencyRequirement,
    FileHotspot,
    RepositorySummary,
)

__version__ = "0.1.0"

__all__ = [
    "ContributorStat",
    "DependencyRequirement",
    "FileHotspot",
    "RepositorySummary",
    "__version__",
    "load_dependencies",
    "load_history",
    "parse_requirement",
    "summarize_repository",
]
