"""Tests for JSON and Markdown report generation."""

import json
from datetime import UTC, datetime
from pathlib import Path

from repovitals.models import (
    ContributorStat,
    DependencyHealth,
    DependencyRequirement,
    FileHotspot,
    PackageMetadata,
    RepositorySummary,
)
from repovitals.reporting import (
    build_report_data,
    create_markdown_report,
    write_reports,
)


def sample_summary() -> RepositorySummary:
    """Return a sample repository summary."""
    return RepositorySummary(
        path=Path("example"),
        commit_count=12,
        contributor_count=2,
        file_count=8,
        additions=500,
        deletions=100,
        binary_changes=1,
        renamed_changes=2,
        first_commit=datetime(2024, 1, 1, tzinfo=UTC),
        latest_commit=datetime(2026, 1, 1, tzinfo=UTC),
        top_contributors=(
            ContributorStat(
                name="Alice",
                email="alice@example.com",
                commits=9,
                share=0.75,
            ),
        ),
        hotspots=(
            FileHotspot(
                path="src/app.py",
                commits=5,
                additions=300,
                deletions=50,
            ),
        ),
    )


def sample_dependencies() -> tuple[DependencyHealth, ...]:
    """Return one sample dependency result."""
    requirement = DependencyRequirement(
        name="example",
        specifier=">=1.0",
        extras=(),
        marker=None,
        url=None,
        raw="example>=1.0",
    )
    metadata = PackageMetadata(
        name="example",
        version="2.0.0",
        summary="Example package",
        package_url="https://pypi.org/project/example/",
        source_url="https://github.com/example/project",
        latest_release=datetime(2025, 10, 1, tzinfo=UTC),
        release_count=5,
        requires_python=">=3.10",
    )

    return (
        DependencyHealth(
            requirement=requirement,
            metadata=metadata,
            risk="low",
            score=0,
            reasons=("A release was published within the last year",),
        ),
    )


def test_build_report_data_is_json_compatible() -> None:
    data = build_report_data(
        sample_summary(),
        sample_dependencies(),
    )

    encoded = json.dumps(data)

    assert '"commit_count": 12' in encoded
    assert data["repository"]["churn"] == 600
    assert data["dependencies"][0]["risk"] == "low"


def test_create_markdown_report_contains_sections() -> None:
    report = create_markdown_report(
        sample_summary(),
        sample_dependencies(),
    )

    assert "# RepoVitals report" in report
    assert "## Repository summary" in report
    assert "## Top contributors" in report
    assert "## File hotspots" in report
    assert "## Direct dependency health" in report
    assert "Alice" in report
    assert "src/app.py" in report


def test_write_reports_creates_files(tmp_path: Path) -> None:
    markdown_path, json_path = write_reports(
        tmp_path,
        sample_summary(),
        sample_dependencies(),
    )

    assert markdown_path.exists()
    assert json_path.exists()
    assert "# RepoVitals report" in markdown_path.read_text(encoding="utf-8")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["repository"]["commit_count"] == 12
