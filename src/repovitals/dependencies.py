"""Read direct dependencies from Python project configuration."""

import tomllib
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement

from repovitals.errors import ConfigurationError
from repovitals.models import DependencyRequirement


def parse_requirement(value: str) -> DependencyRequirement:
    """Parse one Python dependency declaration.

    Examples include:

    - ``pandas>=3.0``
    - ``requests[security]>=2.0``
    - ``colorama; sys_platform == "win32"``
    """
    try:
        requirement = Requirement(value)
    except InvalidRequirement as error:
        raise ConfigurationError(
            f"Invalid dependency declaration: {value!r}"
        ) from error

    marker = str(requirement.marker) if requirement.marker else None

    return DependencyRequirement(
        name=requirement.name,
        specifier=str(requirement.specifier),
        extras=tuple(sorted(requirement.extras)),
        marker=marker,
        url=requirement.url,
        raw=value,
    )


def read_pyproject(project_path: str | Path) -> dict:
    """Read and return a project's ``pyproject.toml`` data."""
    path = Path(project_path).expanduser().resolve()

    if path.is_dir():
        pyproject_path = path / "pyproject.toml"
    else:
        pyproject_path = path

    if not pyproject_path.exists():
        raise ConfigurationError(f"pyproject.toml was not found at: {pyproject_path}")

    if not pyproject_path.is_file():
        raise ConfigurationError(f"pyproject.toml is not a file: {pyproject_path}")

    try:
        with pyproject_path.open("rb") as file:
            return tomllib.load(file)
    except tomllib.TOMLDecodeError as error:
        raise ConfigurationError(
            f"Could not parse {pyproject_path}: {error}"
        ) from error
    except OSError as error:
        raise ConfigurationError(f"Could not read {pyproject_path}: {error}") from error


def load_dependencies(
    project_path: str | Path,
) -> tuple[DependencyRequirement, ...]:
    """Load direct dependencies from ``[project].dependencies``."""
    configuration = read_pyproject(project_path)
    project = configuration.get("project", {})
    values = project.get("dependencies", [])

    if not isinstance(values, list):
        raise ConfigurationError("[project].dependencies must be a list")

    dependencies = []

    for value in values:
        if not isinstance(value, str):
            raise ConfigurationError("Every dependency declaration must be a string")

        dependencies.append(parse_requirement(value))

    return tuple(dependencies)
