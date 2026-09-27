# RepoVitals

RepoVitals is a Python command-line tool that analyzes the maintenance health
of a local Git repository and its direct Python dependencies.

The project combines local Git-history analysis with package metadata from
PyPI. It produces explainable metrics, saved visualizations, and a Markdown
report.

## Planned features

### Local repository analysis

- Count commits and contributors
- Show commit activity over time
- Identify the most active contributors
- Calculate contributor concentration
- Identify files with high line churn
- Find files that have not changed recently
- Handle binary files and renamed paths

### Dependency analysis

- Read direct dependencies from `pyproject.toml`
- Retrieve package and release information from PyPI
- Find the source repository when metadata is available
- Measure time since the latest package release
- Identify packages with missing or stale metadata
- Calculate a simple and explainable maintenance-risk rating
- Cache API responses for reproducibility

### Reports

- Print a summary in the terminal
- Save analysis data as JSON
- Generate a Markdown health report
- Save activity and hotspot visualizations as PNG files

## Requirements

- Python 3.12 or newer
- Git
- [`uv`](https://docs.astral.sh/uv/)

## Installation for development

Clone the repository:

```bash
git clone https://github.com/mustafabukhari/repovitals.git
cd repovitals
```

Install the project and its dependencies:

```bash
uv sync
```

## Current usage

Show the current command-line placeholder:

```bash
uv run -m repovitals /path/to/repository
```

For example, analyze the current directory:

```bash
uv run -m repovitals .
```

After installation, the console entry point is also available:

```bash
uv run repovitals .
```

The complete analysis commands will be documented as they are implemented.

## Playground

The `playground/` directory contains experimental scripts used to test ideas
before moving them into the package.

To run the current Git-history experiment:

```bash
uv run python playground/test.py
```

The experiment expects a local clone of the Requests repository at:

```text
playground/repos/requests
```

It can be cloned with:

```bash
git clone https://github.com/psf/requests.git playground/repos/requests
```

Repositories inside `playground/repos/` are excluded from version control.

## Development

Run the tests:

```bash
uv run pytest
```

Run the linter:

```bash
uv run ruff check .
```

Format the code:

```bash
uv run ruff format .
```

Check formatting without changing files:

```bash
uv run ruff format --check .
```