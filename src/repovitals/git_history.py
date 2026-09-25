"""Read and parse history from a local Git repository."""

import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

from repovitals.errors import (
    GitCommandError,
    GitNotFoundError,
    GitParseError,
    RepositoryError,
)

# Git places this uncommon control character between commit fields.
FIELD_SEPARATOR = "\x1f"

# A commit header begins with this marker.
COMMIT_MARKER = f"{FIELD_SEPARATOR}C{FIELD_SEPARATOR}"

# Hash, author name, email, Unix timestamp, and commit subject.
LOG_FORMAT = FIELD_SEPARATOR.join(["", "C", "%H", "%an", "%ae", "%at", "%s"])

HISTORY_COLUMNS = [
    "sha",
    "author_name",
    "author_email",
    "timestamp",
    "subject",
    "added",
    "deleted",
    "path",
    "is_binary",
    "was_renamed",
]


def run_git(
    arguments: list[str],
    repo_path: Path,
) -> str:
    """Run a Git command and return its standard output.

    Args:
        arguments: Git arguments without the initial ``git`` command.
        repo_path: Directory in which Git should run.

    Raises:
        GitNotFoundError: If the Git executable cannot be found.
        GitCommandError: If Git returns an unsuccessful exit status.
    """
    command = ["git", *arguments]

    try:
        result = subprocess.run(
            command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except FileNotFoundError as error:
        raise GitNotFoundError(
            "Git is not installed or is not available on PATH."
        ) from error
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or error.stdout.strip()

        if not message:
            message = f"Git exited with status {error.returncode}."

        raise GitCommandError(message) from error

    return result.stdout


def find_repository_root(repo_path: str | Path) -> Path:
    """Validate a path and return the root of its Git repository.

    The supplied path can be either the repository root or a directory
    somewhere inside the repository.

    Args:
        repo_path: Path to a local Git repository.

    Returns:
        The absolute path to the root of the Git work tree.

    Raises:
        RepositoryError: If the path is missing or is not a directory.
        GitCommandError: If the path is not inside a Git repository.
    """
    path = Path(repo_path).expanduser()

    if not path.exists():
        raise RepositoryError(f"Path does not exist: {path}")

    if not path.is_dir():
        raise RepositoryError(f"Path is not a directory: {path}")

    path = path.resolve()

    output = run_git(
        ["rev-parse", "--show-toplevel"],
        repo_path=path,
    )
    root = output.strip()

    if not root:
        raise RepositoryError(f"Could not determine the repository root for: {path}")

    return Path(root).resolve()


def read_git_log(repo_path: str | Path) -> tuple[Path, str]:
    """Read machine-readable history from a local Git repository.

    Returns:
        A tuple containing the repository root and raw Git output.
    """
    repository_root = find_repository_root(repo_path)

    output = run_git(
        [
            "-c",
            "i18n.logOutputEncoding=utf-8",
            "-c",
            "core.quotepath=false",
            "log",
            "--no-merges",
            "--numstat",
            "--find-renames",
            f"--pretty=format:{LOG_FORMAT}",
        ],
        repo_path=repository_root,
    )

    return repository_root, output


def parse_count(value: str) -> int:
    """Convert a Git numstat value into a line count.

    Git uses ``-`` for binary files because additions and deletions cannot
    be represented as meaningful line counts.
    """
    if value == "-":
        return 0

    try:
        return int(value)
    except ValueError as error:
        raise GitParseError(
            f"Invalid line-count value in Git output: {value!r}"
        ) from error


def clean_path(path: str) -> str:
    """Return the destination path from Git rename notation.

    Git usually represents renamed files in one of these forms:

    ``old_name.py => new_name.py``

    ``{old_directory => new_directory}/module.py``
    """
    if "=>" not in path:
        return path

    if "{" in path and "}" in path:
        start = path.index("{")
        end = path.index("}", start)

        rename_expression = path[start + 1 : end]
        destination = rename_expression.split("=>", maxsplit=1)[1].strip()

        cleaned_path = path[:start] + destination + path[end + 1 :]
        return cleaned_path.replace("//", "/").lstrip("/")

    return path.split("=>", maxsplit=1)[1].strip()


def parse_log(text: str) -> list[dict[str, Any]]:
    """Convert raw Git output into one dictionary per changed file."""
    rows: list[dict[str, Any]] = []
    current_commit: dict[str, Any] | None = None

    for line_number, line in enumerate(text.split("\n"), start=1):
        if line.startswith(COMMIT_MARKER):
            commit_text = line[len(COMMIT_MARKER) :]
            fields = commit_text.split(FIELD_SEPARATOR, maxsplit=4)

            if len(fields) != 5:
                raise GitParseError(
                    f"Invalid commit record on line {line_number}: {line!r}"
                )

            sha, author_name, author_email, timestamp, subject = fields

            try:
                parsed_timestamp = int(timestamp)
            except ValueError as error:
                raise GitParseError(
                    f"Invalid commit timestamp on line {line_number}: {timestamp!r}"
                ) from error

            current_commit = {
                "sha": sha,
                "author_name": author_name,
                "author_email": author_email,
                "timestamp": parsed_timestamp,
                "subject": subject,
            }
            continue

        if not line.strip() or current_commit is None:
            continue

        parts = line.split("\t", maxsplit=2)

        if len(parts) != 3:
            raise GitParseError(
                f"Invalid file-change record on line {line_number}: {line!r}"
            )

        added_text, deleted_text, original_path = parts
        is_binary = added_text == "-" or deleted_text == "-"

        row = dict(current_commit)
        row["added"] = parse_count(added_text)
        row["deleted"] = parse_count(deleted_text)
        row["path"] = clean_path(original_path)
        row["is_binary"] = is_binary
        row["was_renamed"] = "=>" in original_path

        rows.append(row)

    return rows


def create_history_frame(
    rows: list[dict[str, Any]],
) -> pd.DataFrame:
    """Create a consistently structured DataFrame from history records."""
    frame = pd.DataFrame(rows, columns=HISTORY_COLUMNS)

    if frame.empty:
        frame["date"] = pd.Series(dtype="datetime64[ns, UTC]")
        return frame

    frame["date"] = pd.to_datetime(
        frame["timestamp"],
        unit="s",
        utc=True,
    )

    return frame


def load_history(
    repo_path: str | Path,
) -> tuple[Path, pd.DataFrame]:
    """Load the per-file change history of a Git repository.

    Args:
        repo_path: Repository root or a directory inside the repository.

    Returns:
        A tuple containing the repository root and history DataFrame.
    """
    repository_root, output = read_git_log(repo_path)
    rows = parse_log(output)
    frame = create_history_frame(rows)

    return repository_root, frame
