"""Create and save repository-health visualizations."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from repovitals.errors import PlotError
from repovitals.models import RepositorySummary


def _normalise_commit_dates(history: pd.DataFrame) -> pd.DataFrame:
    """Return unique commits with timezone-naive UTC timestamps."""
    required_columns = {"sha", "date"}
    missing_columns = required_columns - set(history.columns)

    if missing_columns:
        raise ValueError(
            "Commit history is missing required columns: "
            f"{', '.join(sorted(missing_columns))}"
        )

    commits = history[["sha", "date"]].drop_duplicates("sha").copy()

    # utc=True safely handles both timezone-aware Git timestamps and naive
    # timestamps. Matplotlib and resample work more predictably with naive UTC.
    commits["date"] = pd.to_datetime(
        commits["date"],
        utc=True,
        errors="coerce",
    )

    commits = commits.dropna(subset=["date"])

    if commits.empty:
        return commits

    commits["date"] = commits["date"].dt.tz_localize(None)
    return commits.sort_values("date")


def _activity_settings(
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, object]:
    """
    Select aggregation and axis formatting from the actual history span.

    Hourly bars are useful for intensive short-lived work, such as a repository
    created or analysed over one or two weeks. Longer periods use daily, weekly,
    monthly, quarterly or yearly aggregation to keep the graph readable.
    """
    span_hours = max((end - start).total_seconds() / 3600.0, 1.0)
    span_days = span_hours / 24.0

    if span_days <= 14:
        return {
            "frequency": "h",
            "label": "Hour",
            "title": "Hourly commit activity",
            "style": "bar",
            "bar_width_days": 0.8 / 24.0,
            "locator": mdates.HourLocator(interval=6 if span_days <= 4 else 12),
            "formatter": mdates.DateFormatter("%d %b\n%H:%M"),
        }

    if span_days <= 90:
        return {
            "frequency": "D",
            "label": "Day",
            "title": "Daily commit activity",
            "style": "bar",
            "bar_width_days": 0.8,
            "locator": mdates.DayLocator(interval=max(1, round(span_days / 10))),
            "formatter": mdates.DateFormatter("%d %b"),
        }

    if span_days <= 365:
        return {
            "frequency": "W-MON",
            "label": "Week beginning",
            "title": "Weekly commit activity",
            "style": "bar",
            "bar_width_days": 5.5,
            "locator": mdates.WeekdayLocator(
                byweekday=mdates.MO,
                interval=max(1, round(span_days / 70)),
            ),
            "formatter": mdates.DateFormatter("%d %b\n%Y"),
        }

    if span_days <= 1_095:  # About three years.
        return {
            "frequency": "MS",
            "label": "Month",
            "title": "Monthly commit activity",
            "style": "bar",
            "bar_width_days": 20,
            "locator": mdates.MonthLocator(interval=1 if span_days <= 540 else 2),
            "formatter": mdates.DateFormatter("%b\n%Y"),
        }

    if span_days <= 3_650:  # About ten years.
        return {
            "frequency": "QS",
            "label": "Quarter",
            "title": "Quarterly commit activity",
            "style": "line",
            "bar_width_days": 0,
            "locator": mdates.MonthLocator(
                bymonth=[1, 4, 7, 10],
            ),
            "formatter": mdates.DateFormatter("%b\n%Y"),
        }

    return {
        "frequency": "YS",
        "label": "Year",
        "title": "Yearly commit activity",
        "style": "line",
        "bar_width_days": 0,
        "locator": mdates.YearLocator(base=max(1, round(span_days / 3650))),
        "formatter": mdates.DateFormatter("%Y"),
    }


def _activity_figure_width(
    start: pd.Timestamp,
    end: pd.Timestamp,
    frequency: str,
) -> float:
    """Return a practical width based on the displayed number of periods."""
    span_days = max((end - start).total_seconds() / 86400.0, 1.0)

    periods_per_day = {
        "h": 24.0,
        "D": 1.0,
        "W-MON": 1.0 / 7.0,
        "MS": 1.0 / 30.4,
        "QS": 1.0 / 91.3,
        "YS": 1.0 / 365.25,
    }

    period_count = span_days * periods_per_day.get(
        frequency,
        1.0 / 30.4,
    )

    # Do not make an enormous image for hourly data. Axis locators control
    # label density; width provides enough room for the chart itself.
    return min(18.0, max(9.0, 7.0 + period_count * 0.035))


def _save_figure(
    figure: plt.Figure,
    path: Path,
) -> Path:
    """Save, close and return a plot path with consistent error handling."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(
            path,
            dpi=160,
            bbox_inches="tight",
        )
    except OSError as error:
        raise PlotError(f"Could not save plot {path}: {error}") from error
    finally:
        plt.close(figure)

    return path.resolve()


def plot_commit_activity(
    history: pd.DataFrame,
    output_path: str | Path,
) -> Path | None:
    """
    Save commit activity at an appropriate time granularity.

    Aggregation:
    - up to 14 days: hourly bars;
    - 15 to 90 days: daily bars;
    - 3 to 12 months: weekly bars;
    - 1 to 3 years: monthly bars;
    - 3 to 10 years: quarterly line chart;
    - over 10 years: yearly line chart.
    """
    if history.empty:
        return None

    commits = _normalise_commit_dates(history)

    if commits.empty:
        return None

    start = commits["date"].min().floor("h")
    end = commits["date"].max().ceil("h")

    settings = _activity_settings(start, end)
    frequency = str(settings["frequency"])

    activity = (
        commits.set_index("date")
        .resample(frequency)
        .size()
        .asfreq(frequency, fill_value=0)
    )

    path = Path(output_path)
    width = _activity_figure_width(start, end, frequency)

    figure, axis = plt.subplots(figsize=(width, 4.5))

    if settings["style"] == "bar":
        axis.bar(
            activity.index,
            activity.values,
            width=float(settings["bar_width_days"]),
            color="#00549F",
            alpha=0.88,
            align="center",
        )
    else:
        axis.plot(
            activity.index,
            activity.values,
            color="#00549F",
            linewidth=1.8,
            marker="o",
            markersize=3.5,
        )
        axis.fill_between(
            activity.index,
            activity.values,
            color="#00549F",
            alpha=0.12,
        )

    axis.set_title(
        f"{settings['title']} "
        f"({start.strftime('%d %b %Y')} – "
        f"{end.strftime('%d %b %Y')})"
    )
    axis.set_xlabel(str(settings["label"]))
    axis.set_ylabel("Commits")

    axis.xaxis.set_major_locator(settings["locator"])
    axis.xaxis.set_major_formatter(settings["formatter"])

    # Add a small visual margin around the actual activity range.
    if frequency == "h":
        padding = pd.Timedelta(hours=1)
    elif frequency == "D":
        padding = pd.Timedelta(days=1)
    elif frequency == "W-MON":
        padding = pd.Timedelta(days=4)
    elif frequency == "MS":
        padding = pd.Timedelta(days=10)
    elif frequency == "QS":
        padding = pd.Timedelta(days=25)
    else:
        padding = pd.Timedelta(days=90)

    axis.set_xlim(
        activity.index.min() - padding,
        activity.index.max() + padding,
    )
    axis.set_ylim(bottom=0)
    axis.grid(axis="y", alpha=0.25)
    axis.grid(axis="x", alpha=0.10)
    axis.set_axisbelow(True)

    figure.tight_layout()
    return _save_figure(figure, path)


def plot_contributor_share(
    summary: RepositorySummary,
    output_path: str | Path,
) -> Path | None:
    """Save a horizontal bar chart of contributor commit shares."""
    if not summary.top_contributors:
        return None

    contributors = list(reversed(summary.top_contributors))
    names = [contributor.name for contributor in contributors]
    shares = [contributor.share * 100.0 for contributor in contributors]

    path = Path(output_path)

    # Allow one row per contributor plus enough space for long names.
    figure_height = max(3.5, min(12.0, 1.0 + len(contributors) * 0.55))
    figure, axis = plt.subplots(figsize=(9, figure_height))

    axis.barh(names, shares, color="#57AB27")
    axis.set_title("Top contributor commit shares")
    axis.set_xlabel("Share of commits (%)")
    axis.set_xlim(left=0)
    axis.grid(axis="x", alpha=0.25)
    axis.set_axisbelow(True)

    for index, share in enumerate(shares):
        axis.text(
            share,
            index,
            f" {share:.1f}%",
            va="center",
            ha="left",
            fontsize=8.5,
        )

    figure.tight_layout()
    return _save_figure(figure, path)


def plot_file_hotspots(
    summary: RepositorySummary,
    output_path: str | Path,
) -> Path | None:
    """Save a horizontal bar chart of files with the highest line churn."""
    if not summary.hotspots:
        return None

    hotspots = list(reversed(summary.hotspots))
    paths = [hotspot.path for hotspot in hotspots]
    churn = [hotspot.churn for hotspot in hotspots]

    path = Path(output_path)

    # A dynamic height avoids overlapping labels if the hotspot list grows.
    figure_height = max(4.0, min(14.0, 1.2 + len(hotspots) * 0.55))
    figure, axis = plt.subplots(figsize=(11, figure_height))

    axis.barh(paths, churn, color="#F6A800")
    axis.set_title("Files with the highest line churn")
    axis.set_xlabel("Lines added and deleted")
    axis.set_xlim(left=0)
    axis.grid(axis="x", alpha=0.25)
    axis.set_axisbelow(True)

    figure.tight_layout()
    return _save_figure(figure, path)


def create_plots(
    history: pd.DataFrame,
    summary: RepositorySummary,
    output_directory: str | Path,
) -> tuple[Path, ...]:
    """Create every available repository-health plot."""
    directory = Path(output_directory).expanduser().resolve()

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

    return tuple(path for path in candidates if path is not None)
