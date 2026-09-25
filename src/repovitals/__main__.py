"""Command-line interface for RepoVitals."""

import argparse
import sys
from datetime import datetime

from repovitals import __version__
from repovitals.errors import RepoVitalsError
from repovitals.git_history import load_history
from repovitals.metrics import summarize_repository
from repovitals.models import RepositorySummary


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="repovitals",
        description="Analyze a local Git repository.",
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


def main(argv: list[str] | None = None) -> int:
    """Run RepoVitals."""
    parser = create_parser()
    arguments = parser.parse_args(argv)

    if arguments.top < 1:
        parser.error("--top must be at least 1")

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
