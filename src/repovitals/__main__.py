"""Command-line interface for RepoVitals."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from repovitals import __version__
from repovitals.errors import RepoVitalsError
from repovitals.git_history import load_history
from repovitals.health import analyze_dependencies
from repovitals.metrics import summarize_repository
from repovitals.models import DependencyHealth, RepositorySummary


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="repovitals",
        description=(
            "Analyze a local Git repository and its direct Python dependencies."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="repository path (default: current directory)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="number of contributors and hotspots to show",
    )
    parser.add_argument(
        "--no-dependencies",
        action="store_true",
        help="skip dependency analysis",
    )
    parser.add_argument(
        "--cache-dir",
        default=".repovitals-cache",
        help="directory used for cached API responses",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="use cached API responses without network requests",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="ignore cached responses and download fresh metadata",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def format_date(value: datetime | None) -> str:
    """Format a date for terminal output."""
    if value is None:
        return "not available"

    return value.strftime("%Y-%m-%d %H:%M UTC")


def format_summary(summary: RepositorySummary) -> str:
    """Format repository metrics as terminal text."""
    lines = [
        f"RepoVitals {__version__}",
        "",
        f"Repository:       {summary.path}",
        f"Commits:          {summary.commit_count:,}",
        f"Contributors:     {summary.contributor_count:,}",
        f"Files changed:    {summary.file_count:,}",
        f"Lines added:      {summary.additions:,}",
        f"Lines deleted:    {summary.deletions:,}",
        f"Total churn:      {summary.churn:,}",
        f"Binary changes:   {summary.binary_changes:,}",
        f"Renamed changes:  {summary.renamed_changes:,}",
        f"First commit:     {format_date(summary.first_commit)}",
        f"Latest commit:    {format_date(summary.latest_commit)}",
    ]

    if summary.top_contributors:
        lines.extend(["", "Top contributors:"])

        for number, contributor in enumerate(
            summary.top_contributors,
            start=1,
        ):
            lines.append(
                f"{number:>2}. {contributor.name} "
                f"({contributor.commits:,} commits, "
                f"{contributor.share:.1%})"
            )

    if summary.hotspots:
        lines.extend(["", "File hotspots:"])

        for number, hotspot in enumerate(summary.hotspots, start=1):
            lines.append(
                f"{number:>2}. {hotspot.path} "
                f"(churn {hotspot.churn:,}, "
                f"{hotspot.commits:,} commits)"
            )

    if summary.commit_count == 0:
        lines.extend(["", "No commit history was found."])

    return "\n".join(lines)


def format_dependencies(
    dependencies: tuple[DependencyHealth, ...],
) -> str:
    """Format dependency-health results as terminal text."""
    lines = ["Direct dependency health:"]

    if not dependencies:
        lines.append("No direct dependencies were declared.")
        return "\n".join(lines)

    for result in dependencies:
        metadata = result.metadata

        if metadata is None:
            version = "unknown"
            released = "unknown"
        else:
            version = metadata.version
            released = format_date(metadata.latest_release)

        lines.extend(
            [
                "",
                f"- {result.requirement.name}",
                f"  Version: {version}",
                f"  Latest release: {released}",
                f"  Risk: {result.risk} ({result.score}/100)",
            ]
        )

        for reason in result.reasons:
            lines.append(f"  - {reason}")

        if result.error:
            lines.append(f"  - Error: {result.error}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run RepoVitals."""
    parser = create_parser()
    arguments = parser.parse_args(argv)

    if arguments.top < 1:
        parser.error("--top must be at least 1")

    if arguments.offline and arguments.refresh:
        parser.error("--offline and --refresh cannot be used together")

    try:
        repository_root, history = load_history(arguments.path)
        summary = summarize_repository(
            repository_root,
            history,
            limit=arguments.top,
        )
    except RepoVitalsError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(format_summary(summary))

    if arguments.no_dependencies:
        return 0

    pyproject_path = repository_root / "pyproject.toml"

    if not pyproject_path.exists():
        print("\nDependency analysis skipped: pyproject.toml not found.")
        return 0

    cache_directory = Path(arguments.cache_dir)

    try:
        dependencies = analyze_dependencies(
            repository_root,
            cache_directory=cache_directory,
            offline=arguments.offline,
            refresh=arguments.refresh,
        )
    except RepoVitalsError as error:
        print(f"\nDependency analysis failed: {error}")
        return 0

    print()
    print(format_dependencies(dependencies))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
