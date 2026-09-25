"""Create and save repository-health visualizations."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from repovitals.errors import RepoVitalsError
from repovitals.models import RepositorySummary


class PlotError(RepoVitalsError):
    """Raised when a visualization cannot be saved."""


def plot_commit_activity(
    history: pd.DataFrame,
    output_path: str | Path,
) -> Path | None:
    """Save a monthly commit-activity plot."""
    if history.empty:
        return None

    commits = history[["sha", "date"]].drop_duplicates("sha").copy()
    commits["month"] = commits["date"].dt.tz_localize(None).dt.to_period("M")
    activity = commits.groupby("month").size()
    activity.index = activity.index.to_timestamp()

    path = Path(output_path)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        figure, axis = plt.subplots(figsize=(10, 4))
        axis.plot(
            activity.index,
            activity.values,
            color="#00549F",
            linewidth=1.8,
        )
        axis.set_title("Monthly commit activity")
        axis.set_xlabel("Month")
        axis.set_ylabel("Commits")
        axis.grid(alpha=0.25)
        figure.tight_layout()
        figure.savefig(path, dpi=160)
        plt.close(figure)
    except OSError as error:
        raise PlotError(f"Could not save plot {path}: {error}") from error

    return path.resolve()


def plot_contributor_share(
    summary: RepositorySummary,
    output_path: str | Path,
) -> Path | None:
    """Save a horizontal bar chart of contributor commit shares."""
    if not summary.top_contributors:
        return None

    contributors = list(reversed(summary.top_contributors))
    names = [contributor.name for contributor in contributors]
    shares = [contributor.share * 100 for contributor in contributors]
    path = Path(output_path)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        figure, axis = plt.subplots(figsize=(9, 5))
        axis.barh(names, shares, color="#57AB27")
        axis.set_title("Top contributor commit shares")
        axis.set_xlabel("Share of commits (%)")
        figure.tight_layout()
        figure.savefig(path, dpi=160)
        plt.close(figure)
    except OSError as error:
        raise PlotError(f"Could not save plot {path}: {error}") from error

    return path.resolve()


def plot_file_hotspots(
    summary: RepositorySummary,
    output_path: str | Path,
) -> Path | None:
    """Save a horizontal bar chart of file churn."""
    if not summary.hotspots:
        return None

    hotspots = list(reversed(summary.hotspots))
    paths = [hotspot.path for hotspot in hotspots]
    churn = [hotspot.churn for hotspot in hotspots]
    path = Path(output_path)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        figure, axis = plt.subplots(figsize=(10, 6))
        axis.barh(paths, churn, color="#F6A800")
        axis.set_title("Files with the highest line churn")
        axis.set_xlabel("Lines added and deleted")
        figure.tight_layout()
        figure.savefig(path, dpi=160)
        plt.close(figure)
    except OSError as error:
        raise PlotError(f"Could not save plot {path}: {error}") from error

    return path.resolve()


def create_plots(
    history: pd.DataFrame,
    summary: RepositorySummary,
    output_directory: str | Path,
) -> tuple[Path, ...]:
    """Create all available repository plots."""
    directory = Path(output_directory).expanduser().resolve()
    created_paths = []

    candidates = (
        plot_commit_activity(
            history,
            directory / "commit_activity.png",
        ),
        plot_contributor_share(
            summary,
            directory / "contributor_share.png",
        ),
        plot_file_hotspots(
            summary,
            directory / "file_hotspots.png",
        ),
    )

    for path in candidates:
        if path is not None:
            created_paths.append(path)

    return tuple(created_paths)
