"""Calculate metrics from parsed Git history."""

from pathlib import Path

import pandas as pd

from repovitals.models import ContributorStat, FileHotspot, RepositorySummary


def contributor_identity(frame: pd.DataFrame) -> pd.Series:
    """Return a normalized contributor identity for each row."""
    emails = frame["author_email"].fillna("").astype(str).str.strip().str.lower()
    names = frame["author_name"].fillna("").astype(str).str.strip()

    return emails.where(emails != "", names)


def calculate_contributors(
    frame: pd.DataFrame,
    limit: int = 10,
) -> tuple[ContributorStat, ...]:
    """Return contributors ordered by unique commit count."""
    if frame.empty:
        return ()

    working = frame.copy()
    working["identity"] = contributor_identity(working)

    grouped = (
        working.groupby("identity")
        .agg(
            name=("author_name", "last"),
            email=("author_email", "last"),
            commits=("sha", "nunique"),
        )
        .reset_index()
        .sort_values(
            ["commits", "name"],
            ascending=[False, True],
        )
    )

    total_commits = int(frame["sha"].nunique())
    contributors = []

    for row in grouped.head(limit).itertuples():
        contributors.append(
            ContributorStat(
                name=str(row.name),
                email=str(row.email),
                commits=int(row.commits),
                share=float(row.commits / total_commits),
            )
        )

    return tuple(contributors)


def calculate_hotspots(
    frame: pd.DataFrame,
    limit: int = 10,
) -> tuple[FileHotspot, ...]:
    """Return text files ordered by line churn."""
    if frame.empty:
        return ()

    text_changes = frame.loc[~frame["is_binary"]].copy()

    if text_changes.empty:
        return ()

    grouped = (
        text_changes.groupby("path")
        .agg(
            commits=("sha", "nunique"),
            additions=("added", "sum"),
            deletions=("deleted", "sum"),
        )
        .reset_index()
    )

    grouped["churn"] = grouped["additions"] + grouped["deletions"]
    grouped = grouped.sort_values(
        ["churn", "commits", "path"],
        ascending=[False, False, True],
    )

    hotspots = []

    for row in grouped.head(limit).itertuples():
        hotspots.append(
            FileHotspot(
                path=str(row.path),
                commits=int(row.commits),
                additions=int(row.additions),
                deletions=int(row.deletions),
            )
        )

    return tuple(hotspots)


def summarize_repository(
    repository_path: Path,
    frame: pd.DataFrame,
    limit: int = 10,
) -> RepositorySummary:
    """Calculate summary metrics for a repository."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    if frame.empty:
        return RepositorySummary(
            path=repository_path,
            commit_count=0,
            contributor_count=0,
            file_count=0,
            additions=0,
            deletions=0,
            binary_changes=0,
            renamed_changes=0,
            first_commit=None,
            latest_commit=None,
            top_contributors=(),
            hotspots=(),
        )

    text_changes = frame.loc[~frame["is_binary"]]

    return RepositorySummary(
        path=repository_path,
        commit_count=int(frame["sha"].nunique()),
        contributor_count=int(contributor_identity(frame).nunique()),
        file_count=int(frame["path"].nunique()),
        additions=int(text_changes["added"].sum()),
        deletions=int(text_changes["deleted"].sum()),
        binary_changes=int(frame["is_binary"].sum()),
        renamed_changes=int(frame["was_renamed"].sum()),
        first_commit=frame["date"].min().to_pydatetime(),
        latest_commit=frame["date"].max().to_pydatetime(),
        top_contributors=calculate_contributors(frame, limit),
        hotspots=calculate_hotspots(frame, limit),
    )
