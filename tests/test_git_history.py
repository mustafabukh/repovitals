"""Tests for Git-history parsing."""

import pandas as pd
import pytest
from pandas.api.types import is_datetime64_any_dtype

from repovitals.errors import GitParseError, RepositoryError
from repovitals.git_history import (
    COMMIT_MARKER,
    FIELD_SEPARATOR,
    clean_path,
    create_history_frame,
    find_repository_root,
    parse_count,
    parse_log,
)


def make_commit_line(
    sha: str,
    author_name: str,
    author_email: str,
    timestamp: int,
    subject: str,
) -> str:
    """Create a commit line using RepoVitals' Git output format."""
    fields = [
        sha,
        author_name,
        author_email,
        str(timestamp),
        subject,
    ]

    return COMMIT_MARKER + FIELD_SEPARATOR.join(fields)


def test_parse_count_returns_integer() -> None:
    assert parse_count("42") == 42


def test_parse_count_returns_zero_for_binary_marker() -> None:
    assert parse_count("-") == 0


def test_parse_count_rejects_invalid_value() -> None:
    with pytest.raises(GitParseError, match="Invalid line-count value"):
        parse_count("not-a-number")


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("src/module.py", "src/module.py"),
        ("old_name.py => new_name.py", "new_name.py"),
        (
            "{requests => src/requests}/api.py",
            "src/requests/api.py",
        ),
    ],
)
def test_clean_path(original: str, expected: str) -> None:
    assert clean_path(original) == expected


def test_parse_log_creates_one_row_per_file_change() -> None:
    text = "\n".join(
        [
            make_commit_line(
                "abc123",
                "Alice Example",
                "alice@example.com",
                1_700_000_000,
                "Add application",
            ),
            "10\t2\tsrc/app.py",
            "5\t1\tREADME.md",
            make_commit_line(
                "def456",
                "Bob Example",
                "bob@example.com",
                1_700_086_400,
                "Add tests",
            ),
            "20\t3\ttests/test_app.py",
        ]
    )

    rows = parse_log(text)

    assert len(rows) == 3

    assert rows[0]["sha"] == "abc123"
    assert rows[0]["author_name"] == "Alice Example"
    assert rows[0]["added"] == 10
    assert rows[0]["deleted"] == 2
    assert rows[0]["path"] == "src/app.py"

    assert rows[2]["sha"] == "def456"
    assert rows[2]["subject"] == "Add tests"
    assert rows[2]["path"] == "tests/test_app.py"


def test_parse_log_marks_binary_file_changes() -> None:
    text = "\n".join(
        [
            make_commit_line(
                "abc123",
                "Alice",
                "alice@example.com",
                1_700_000_000,
                "Add logo",
            ),
            "-\t-\tassets/logo.png",
        ]
    )

    rows = parse_log(text)

    assert len(rows) == 1
    assert rows[0]["is_binary"] is True
    assert rows[0]["added"] == 0
    assert rows[0]["deleted"] == 0


def test_parse_log_cleans_renamed_file_path() -> None:
    text = "\n".join(
        [
            make_commit_line(
                "abc123",
                "Alice",
                "alice@example.com",
                1_700_000_000,
                "Move module",
            ),
            "1\t1\t{old => new}/module.py",
        ]
    )

    rows = parse_log(text)

    assert rows[0]["path"] == "new/module.py"
    assert rows[0]["was_renamed"] is True


def test_parse_log_rejects_invalid_file_change() -> None:
    text = "\n".join(
        [
            make_commit_line(
                "abc123",
                "Alice",
                "alice@example.com",
                1_700_000_000,
                "Invalid change",
            ),
            "this line is not valid numstat output",
        ]
    )

    with pytest.raises(
        GitParseError,
        match="Invalid file-change record",
    ):
        parse_log(text)


def test_create_history_frame_adds_utc_date() -> None:
    text = "\n".join(
        [
            make_commit_line(
                "abc123",
                "Alice",
                "alice@example.com",
                1_700_000_000,
                "Add application",
            ),
            "10\t2\tsrc/app.py",
        ]
    )

    frame = create_history_frame(parse_log(text))

    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 1
    assert "date" in frame.columns
    assert is_datetime64_any_dtype(frame["date"])
    assert str(frame["date"].dt.tz) == "UTC"


def test_create_history_frame_handles_empty_history() -> None:
    frame = create_history_frame([])

    assert frame.empty
    assert "date" in frame.columns
    assert is_datetime64_any_dtype(frame["date"])
    assert str(frame["date"].dt.tz) == "UTC"


def test_find_repository_root_rejects_missing_path(
    tmp_path,
) -> None:
    missing_path = tmp_path / "does-not-exist"

    with pytest.raises(RepositoryError, match="Path does not exist"):
        find_repository_root(missing_path)


def test_find_repository_root_rejects_file_path(
    tmp_path,
) -> None:
    file_path = tmp_path / "example.txt"
    file_path.write_text("example", encoding="utf-8")

    with pytest.raises(RepositoryError, match="Path is not a directory"):
        find_repository_root(file_path)
