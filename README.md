# RepoVitals

RepoVitals is a Python command-line tool for reviewing the maintenance activity of a local Git repository and the direct Python dependencies in its `pyproject.toml`.

It summarizes commit and contributor activity, identifies files with high line churn, retrieves package metadata from PyPI, and can save a Markdown report, JSON data, and PNG charts. Dependency risk scores are review helpers.

## Requirements

- Python 3.12 or newer
- Git available on `PATH`
- [`uv`](https://docs.astral.sh/uv/) for the development commands below
- Network access for uncached PyPI metadata, unless using `--offline`

## Install

```bash
git clone https://github.com/mustafabukh/repovitals.git
cd repovitals
uv sync
```

Run the installed package with either its module entry point or console script:

```bash
uv run -m repovitals --help
uv run repovitals --help
```

## Quick start

Analyze the current Git repository:

```bash
uv run -m repovitals .
```

- or with reports saved to 

```bash
uv run -m repovitals . --output repovitals-report
```

Analyze another local repository and save reports and charts:
- example (on requests lib repo in playground): 

```bash
uv run -m repovitals ./playground/repos/requests --output requests-reports
```

Run Git analysis without querying dependencies:

```bash
uv run -m repovitals /path/to/repository --no-dependencies
```

A supplied path may be the repository root or a directory inside it. RepoVitals finds the Git work-tree root and reads its history. Dependency analysis looks for `pyproject.toml` **at that root**.

### Options

| Option | Effect |
|---|---|
| `path` | Local repository path; defaults to `.` |
| `--top N` | Show up to `N` contributors and file hotspots; default: `10` |
| `--no-dependencies` | Skip dependency analysis |
| `--cache-dir DIR` | Store PyPI JSON responses in `DIR`; default: `.repovitals-cache` |
| `--offline` | Use cached PyPI responses only; make no PyPI requests |
| `--refresh` | Download fresh PyPI responses instead of reading cached ones |
| `--output DIR` | Save Markdown and JSON reports and available PNG charts in `DIR` |
| `--version` | Print the installed version |

`--offline` and `--refresh` cannot be used together. 
`--top` must be at least `1`.

The cache directory is interpreted relative to the directory **from which you run the command**, unless you supply an absolute path.

## What is analyzed

### Git history

RepoVitals reads non-merge commits using Git's `--numstat` output. It reports:

- Unique commits and contributors represented in the parsed file-change history
- Unique changed paths
- Text-line additions, deletions, and total churn
- Counts of binary and renamed file changes
- First and latest commit dates
- Top contributors by unique commit count and their share of counted commits
- Text-file hotspots ranked by total lines added plus deleted

Binary changes count as file changes, but their additions and deletions contribute **zero** to line churn because Git does not provide meaningful line counts for binary files. Rename notation is normalized to the destination path for hotspot reporting.

The tool analyzes historical changes; it does not determine whether a file still exists or identify files that have gone stale. Merge commits are not analyzed.

### Direct Python dependencies

When the repository root contains a `pyproject.toml`, RepoVitals reads **`[project].dependencies`** and requests metadata for those direct dependencies from PyPI.

The risk score uses three signals:

| Signal | Added score |
|---|---:|
| No release date found | 40 |
| Latest release over one year old | 20 |
| Latest release over two years old | 40 instead of 20 |
| Latest release over three years old | 60 instead of 40 |
| No likely source URL found in PyPI metadata | 20 |
| Fewer than two published releases found | 10 |

Scores are capped at 100. A score below 25 is **low** risk, 25–49 is **moderate**, and 50 or above is **high**. If metadata cannot be retrieved, risk is **unknown**.

### offline use

Successful PyPI responses are saved as JSON in the cache directory. Later runs reuse those responses unless `--refresh` is set:

```bash
uv run -m repovitals . --refresh
uv run -m repovitals . --offline
```

Offline mode still analyzes the local Git repository. Packages without cached responses receive an **unknown** risk result with an explanatory error.

## Saved output

With `--output reports`, RepoVitals writes:

```text
reports/
├── report.md
├── report.json
├── commit_activity.png       # if commit activity is available
├── contributor_share.png     # if contributor data is available
└── file_hotspots.png         # if text-file hotspots are available
```

`report.md` summarizes the results for reading; `report.json` contains the structured data. The charts show commit activity over time, top contributors' commit shares, and files with the most line churn. The commit-activity chart adjusts its time aggregation to the span of the repository history.

For example:

```bash
uv run -m repovitals . --output reports
```
## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```
