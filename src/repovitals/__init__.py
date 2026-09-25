"""Analyze the health of Git repositories and Python dependencies."""

from repovitals.dependencies import load_dependencies, parse_requirement
from repovitals.git_history import load_history
from repovitals.health import analyze_dependencies, assess_package
from repovitals.metrics import summarize_repository
from repovitals.models import (
    ContributorStat,
    DependencyHealth,
    DependencyRequirement,
    FileHotspot,
    PackageMetadata,
    RepositorySummary,
)
from repovitals.pypi import load_package_metadata

__version__ = "0.1.0"

__all__ = [
    "ContributorStat",
    "DependencyHealth",
    "DependencyRequirement",
    "FileHotspot",
    "PackageMetadata",
    "RepositorySummary",
    "__version__",
    "analyze_dependencies",
    "assess_package",
    "load_dependencies",
    "load_history",
    "load_package_metadata",
    "parse_requirement",
    "summarize_repository",
]
