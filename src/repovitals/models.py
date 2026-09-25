"""Data models returned by repository analysis."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class ContributorStat:
    """Commit statistics for one contributor."""

    name: str
    email: str
    commits: int
    share: float


@dataclass(frozen=True)
class FileHotspot:
    """Change statistics for one file."""

    path: str
    commits: int
    additions: int
    deletions: int

    @property
    def churn(self) -> int:
        """Return additions plus deletions."""
        return self.additions + self.deletions


@dataclass(frozen=True)
class RepositorySummary:
    """Summary of a local Git repository."""

    path: Path
    commit_count: int
    contributor_count: int
    file_count: int
    additions: int
    deletions: int
    binary_changes: int
    renamed_changes: int
    first_commit: datetime | None
    latest_commit: datetime | None
    top_contributors: tuple[ContributorStat, ...]
    hotspots: tuple[FileHotspot, ...]

    @property
    def churn(self) -> int:
        """Return total line churn."""
        return self.additions + self.deletions


@dataclass(frozen=True)
class DependencyRequirement:
    """A direct dependency declared by a Python project."""

    name: str
    specifier: str
    extras: tuple[str, ...]
    marker: str | None
    url: str | None
    raw: str
