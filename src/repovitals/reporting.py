"""Generate JSON and Markdown analysis reports."""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repovitals.errors import RepoVitalsError
from repovitals.models import DependencyHealth, RepositorySummary


class ReportError(RepoVitalsError):
    """Raised when an analysis report cannot be written."""


def datetime_to_text(value: datetime | None) -> str | None:
    """Convert an optional datetime to ISO 8601 text."""
    return value.isoformat() if value is not None else None


def repository_to_dict(
    summary: RepositorySummary,
) -> dict[str, Any]:
    """Convert a repository summary into JSON-compatible data."""
    return {
        "path": str(summary.path),
        "commit_count": summary.commit_count,
        "contributor_count": summary.contributor_count,
        "file_count": summary.file_count,
        "additions": summary.additions,
        "deletions": summary.deletions,
        "churn": summary.churn,
        "binary_changes": summary.binary_changes,
        "renamed_changes": summary.renamed_changes,
        "first_commit": datetime_to_text(summary.first_commit),
        "latest_commit": datetime_to_text(summary.latest_commit),
        "top_contributors": [
            asdict(contributor) for contributor in summary.top_contributors
        ],
        "hotspots": [
            {
                **asdict(hotspot),
                "churn": hotspot.churn,
            }
            for hotspot in summary.hotspots
        ],
    }


def dependency_to_dict(
    result: DependencyHealth,
) -> dict[str, Any]:
    """Convert one dependency result into JSON-compatible data."""
    metadata = result.metadata

    return {
        "requirement": {
            "name": result.requirement.name,
            "specifier": result.requirement.specifier,
            "extras": list(result.requirement.extras),
            "marker": result.requirement.marker,
            "url": result.requirement.url,
            "raw": result.requirement.raw,
        },
        "metadata": (
            {
                "name": metadata.name,
                "version": metadata.version,
                "summary": metadata.summary,
                "package_url": metadata.package_url,
                "source_url": metadata.source_url,
                "latest_release": datetime_to_text(metadata.latest_release),
                "release_count": metadata.release_count,
                "requires_python": metadata.requires_python,
            }
            if metadata is not None
            else None
        ),
        "risk": result.risk,
        "score": result.score,
        "reasons": list(result.reasons),
        "error": result.error,
    }


def build_report_data(
    summary: RepositorySummary,
    dependencies: tuple[DependencyHealth, ...],
) -> dict[str, Any]:
    """Build the complete JSON-compatible report structure."""
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "repository": repository_to_dict(summary),
        "dependencies": [dependency_to_dict(result) for result in dependencies],
    }


def format_markdown_date(value: datetime | None) -> str:
    """Format an optional datetime for Markdown."""
    if value is None:
        return "Not available"

    return value.strftime("%Y-%m-%d %H:%M UTC")


def create_markdown_report(
    summary: RepositorySummary,
    dependencies: tuple[DependencyHealth, ...],
) -> str:
    """Create a Markdown repository-health report."""
    lines = [
        "# RepoVitals report",
        "",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Repository summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Repository | `{summary.path}` |",
        f"| Commits | {summary.commit_count:,} |",
        f"| Contributors | {summary.contributor_count:,} |",
        f"| Files changed | {summary.file_count:,} |",
        f"| Lines added | {summary.additions:,} |",
        f"| Lines deleted | {summary.deletions:,} |",
        f"| Total churn | {summary.churn:,} |",
        f"| Binary changes | {summary.binary_changes:,} |",
        f"| Renamed changes | {summary.renamed_changes:,} |",
        f"| First commit | {format_markdown_date(summary.first_commit)} |",
        f"| Latest commit | {format_markdown_date(summary.latest_commit)} |",
        "",
        "## Top contributors",
        "",
    ]

    if summary.top_contributors:
        lines.extend(
            [
                "| Contributor | Commits | Share |",
                "|---|---:|---:|",
            ]
        )

        for contributor in summary.top_contributors:
            lines.append(
                f"| {contributor.name} | "
                f"{contributor.commits:,} | "
                f"{contributor.share:.1%} |"
            )
    else:
        lines.append("No contributor data was found.")

    lines.extend(["", "## File hotspots", ""])

    if summary.hotspots:
        lines.extend(
            [
                "| File | Commits | Additions | Deletions | Churn |",
                "|---|---:|---:|---:|---:|",
            ]
        )

        for hotspot in summary.hotspots:
            safe_path = hotspot.path.replace("|", "\\|")
            lines.append(
                f"| `{safe_path}` | "
                f"{hotspot.commits:,} | "
                f"{hotspot.additions:,} | "
                f"{hotspot.deletions:,} | "
                f"{hotspot.churn:,} |"
            )
    else:
        lines.append("No text-file hotspot data was found.")

    lines.extend(["", "## Direct dependency health", ""])

    if not dependencies:
        lines.append("No direct dependencies were analyzed.")
    else:
        lines.extend(
            [
                "| Package | Version | Latest release | Risk | Score |",
                "|---|---|---|---|---:|",
            ]
        )

        for result in dependencies:
            metadata = result.metadata
            version = metadata.version if metadata else "Unknown"
            latest_release = (
                format_markdown_date(metadata.latest_release) if metadata else "Unknown"
            )

            lines.append(
                f"| {result.requirement.name} | "
                f"{version} | {latest_release} | "
                f"{result.risk.title()} | {result.score}/100 |"
            )

        lines.extend(["", "### Dependency findings", ""])

        for result in dependencies:
            lines.append(f"#### {result.requirement.name}")
            lines.append("")

            for reason in result.reasons:
                lines.append(f"- {reason}")

            if result.error:
                lines.append(f"- Error: {result.error}")

            if result.metadata and result.metadata.source_url:
                lines.append(f"- Source: {result.metadata.source_url}")

            lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            "Dependency risk ratings are explainable heuristics based on "
            "release age, release availability, and source-repository "
            "metadata. A quiet project is not necessarily abandoned, so "
            "results should be reviewed rather than treated as proof.",
            "",
        ]
    )

    return "\n".join(lines)


def write_reports(
    output_directory: str | Path,
    summary: RepositorySummary,
    dependencies: tuple[DependencyHealth, ...],
) -> tuple[Path, Path]:
    """Write Markdown and JSON reports and return their paths."""
    output_path = Path(output_directory).expanduser().resolve()
    markdown_path = output_path / "report.md"
    json_path = output_path / "report.json"

    try:
        output_path.mkdir(parents=True, exist_ok=True)

        markdown_path.write_text(
            create_markdown_report(summary, dependencies),
            encoding="utf-8",
        )

        with json_path.open("w", encoding="utf-8") as file:
            json.dump(
                build_report_data(summary, dependencies),
                file,
                indent=2,
                ensure_ascii=False,
            )
            file.write("\n")
    except OSError as error:
        raise ReportError(
            f"Could not write report files in {output_path}: {error}"
        ) from error

    return markdown_path, json_path
