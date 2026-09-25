"""Assess the maintenance health of direct Python dependencies."""

from datetime import UTC, datetime
from pathlib import Path

from repovitals.dependencies import load_dependencies
from repovitals.errors import RepoVitalsError
from repovitals.models import (
    DependencyHealth,
    DependencyRequirement,
    PackageMetadata,
)
from repovitals.pypi import load_package_metadata


def assess_package(
    requirement: DependencyRequirement,
    metadata: PackageMetadata,
    *,
    now: datetime | None = None,
) -> DependencyHealth:
    """Calculate an explainable maintenance-risk rating."""
    current_time = now or datetime.now(UTC)
    score = 0
    reasons = []

    if metadata.latest_release is None:
        score += 40
        reasons.append("No release date was found")
    else:
        release_age_days = (current_time - metadata.latest_release).days

        if release_age_days > 1_095:
            score += 60
            reasons.append("Latest release is more than three years old")
        elif release_age_days > 730:
            score += 40
            reasons.append("Latest release is more than two years old")
        elif release_age_days > 365:
            score += 20
            reasons.append("Latest release is more than one year old")
        else:
            reasons.append("A release was published within the last year")

    if metadata.source_url is None:
        score += 20
        reasons.append("No source repository was found in PyPI metadata")

    if metadata.release_count < 2:
        score += 10
        reasons.append("Fewer than two published releases were found")

    score = min(score, 100)

    if score < 25:
        risk = "low"
    elif score < 50:
        risk = "moderate"
    else:
        risk = "high"

    return DependencyHealth(
        requirement=requirement,
        metadata=metadata,
        risk=risk,
        score=score,
        reasons=tuple(reasons),
    )


def analyze_dependencies(
    project_path: str | Path,
    *,
    cache_directory: str | Path = ".repovitals-cache",
    offline: bool = False,
    refresh: bool = False,
) -> tuple[DependencyHealth, ...]:
    """Analyze all direct dependencies without stopping on one failure."""
    requirements = load_dependencies(project_path)
    results = []

    for requirement in requirements:
        if requirement.url is not None:
            results.append(
                DependencyHealth(
                    requirement=requirement,
                    metadata=None,
                    risk="unknown",
                    score=0,
                    reasons=("Direct URL dependencies are not queried on PyPI",),
                )
            )
            continue

        try:
            metadata = load_package_metadata(
                requirement.name,
                cache_directory=cache_directory,
                offline=offline,
                refresh=refresh,
            )
        except RepoVitalsError as error:
            results.append(
                DependencyHealth(
                    requirement=requirement,
                    metadata=None,
                    risk="unknown",
                    score=0,
                    reasons=("Package metadata could not be retrieved",),
                    error=str(error),
                )
            )
            continue

        results.append(assess_package(requirement, metadata))

    return tuple(results)
