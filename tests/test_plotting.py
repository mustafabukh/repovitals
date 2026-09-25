"""Tests for saved repository visualizations."""

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from repovitals.models import (
    ContributorStat,
    FileHotspot,
    RepositorySummary,
)
from repovitals.plotting import create_plots


def test_create_plots_saves_png_files(tmp_path: Path) -> None:
    history = pd.DataFrame(
        {
            "sha": ["a", "b", "c"],
            "date": pd.to_datetime(
                [
                    "2025-01-01T00:00:00Z",
                    "2025-02-01T00:00:00Z",
                    "2025-02-10T00:00:00Z",
                ],
                utc=True,
            ),
        }
    )

    summary = RepositorySummary(
        path=Path("example"),
        commit_count=3,
        contributor_count=1,
        file_count=1,
        additions=20,
        deletions=5,
        binary_changes=0,
        renamed_changes=0,
        first_commit=datetime(2025, 1, 1, tzinfo=UTC),
        latest_commit=datetime(2025, 2, 10, tzinfo=UTC),
        top_contributors=(
            ContributorStat(
                name="Alice",
                email="alice@example.com",
                commits=3,
                share=1.0,
            ),
        ),
        hotspots=(
            FileHotspot(
                path="src/app.py",
                commits=3,
                additions=20,
                deletions=5,
            ),
        ),
    )

    paths = create_plots(history, summary, tmp_path)

    assert len(paths) == 3

    for path in paths:
        assert path.exists()
        assert path.suffix == ".png"
        assert path.stat().st_size > 0
