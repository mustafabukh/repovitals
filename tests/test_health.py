"""Tests for dependency-health assessment."""

from datetime import UTC, datetime

from repovitals.health import assess_package
from repovitals.models import DependencyRequirement, PackageMetadata


def requirement() -> DependencyRequirement:
    """Return a sample dependency."""
    return DependencyRequirement(
        name="example",
        specifier=">=1.0",
        extras=(),
        marker=None,
        url=None,
        raw="example>=1.0",
    )


def metadata(
    release_date: datetime | None,
    source_url: str | None = "https://github.com/example/project",
    release_count: int = 5,
) -> PackageMetadata:
    """Return sample package metadata."""
    return PackageMetadata(
        name="example",
        version="2.0.0",
        summary="Example package",
        package_url="https://pypi.org/project/example/",
        source_url=source_url,
        latest_release=release_date,
        release_count=release_count,
        requires_python=">=3.10",
    )


def test_recent_package_has_low_risk() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    release = datetime(2025, 10, 1, tzinfo=UTC)

    result = assess_package(
        requirement(),
        metadata(release),
        now=now,
    )

    assert result.risk == "low"
    assert result.score == 0


def test_old_package_has_high_risk() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    release = datetime(2020, 1, 1, tzinfo=UTC)

    result = assess_package(
        requirement(),
        metadata(release),
        now=now,
    )

    assert result.risk == "high"
    assert result.score == 60


def test_missing_metadata_signals_increase_risk() -> None:
    result = assess_package(
        requirement(),
        metadata(
            None,
            source_url=None,
            release_count=1,
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert result.risk == "high"
    assert result.score == 70
    assert len(result.reasons) == 3
