"""Tests for repository metrics."""

from pathlib import Path

from repovitals.git_history import (
    COMMIT_MARKER,
    FIELD_SEPARATOR,
    create_history_frame,
    parse_log,
)
from repovitals.metrics import (
    calculate_contributors,
    calculate_hotspots,
    summarize_repository,
)


def make_commit_line(
    sha: str,
    name: str,
    email: str,
    timestamp: int,
    subject: str,
) -> str:
    """Create a test commit line."""
    fields = [sha, name, email, str(timestamp), subject]
    return COMMIT_MARKER + FIELD_SEPARATOR.join(fields)


def sample_history():
    """Create a small history DataFrame."""
    text = "\n".join(
        [
            make_commit_line(
                "aaa111",
                "Alice",
                "alice@example.com",
                1_700_000_000,
                "Add application",
            ),
            "100\t20\tsrc/app.py",
            "10\t2\tREADME.md",
            make_commit_line(
                "bbb222",
                "Alice",
                "ALICE@example.com",
                1_700_086_400,
                "Update application",
            ),
            "50\t10\tsrc/app.py",
            make_commit_line(
                "ccc333",
                "Bob",
                "bob@example.com",
                1_700_172_800,
                "Add tests",
            ),
            "40\t5\ttests/test_app.py",
            "-\t-\tassets/logo.png",
        ]
    )

    return create_history_frame(parse_log(text))


def test_calculate_contributors_counts_unique_commits() -> None:
    contributors = calculate_contributors(sample_history())

    assert len(contributors) == 2
    assert contributors[0].name == "Alice"
    assert contributors[0].commits == 2
    assert contributors[0].share == 2 / 3
    assert contributors[1].name == "Bob"


def test_calculate_hotspots_orders_by_churn() -> None:
    hotspots = calculate_hotspots(sample_history())

    assert hotspots[0].path == "src/app.py"
    assert hotspots[0].commits == 2
    assert hotspots[0].additions == 150
    assert hotspots[0].deletions == 30
    assert hotspots[0].churn == 180


def test_calculate_hotspots_excludes_binary_files() -> None:
    hotspots = calculate_hotspots(sample_history())
    paths = {hotspot.path for hotspot in hotspots}

    assert "assets/logo.png" not in paths


def test_summarize_repository_returns_totals() -> None:
    summary = summarize_repository(
        Path("example"),
        sample_history(),
    )

    assert summary.commit_count == 3
    assert summary.contributor_count == 2
    assert summary.file_count == 4
    assert summary.additions == 200
    assert summary.deletions == 37
    assert summary.churn == 237
    assert summary.binary_changes == 1
    assert summary.first_commit is not None
    assert summary.latest_commit is not None


def test_summarize_repository_handles_empty_history() -> None:
    summary = summarize_repository(
        Path("empty"),
        create_history_frame([]),
    )

    assert summary.commit_count == 0
    assert summary.contributor_count == 0
    assert summary.churn == 0
    assert summary.top_contributors == ()
    assert summary.hotspots == ()
