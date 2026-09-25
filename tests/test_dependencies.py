"""Tests for Python dependency parsing."""

from pathlib import Path

import pytest

from repovitals.dependencies import (
    load_dependencies,
    parse_requirement,
    read_pyproject,
)
from repovitals.errors import ConfigurationError


def write_pyproject(directory: Path, content: str) -> Path:
    """Write a temporary pyproject.toml file."""
    path = directory / "pyproject.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_simple_requirement() -> None:
    dependency = parse_requirement("pandas>=3.0,<4")

    assert dependency.name == "pandas"
    assert dependency.specifier == "<4,>=3.0"
    assert dependency.extras == ()
    assert dependency.marker is None
    assert dependency.url is None
    assert dependency.raw == "pandas>=3.0,<4"


def test_parse_requirement_with_extras() -> None:
    dependency = parse_requirement("requests[security,socks]>=2.0")

    assert dependency.name == "requests"
    assert dependency.extras == ("security", "socks")
    assert dependency.specifier == ">=2.0"


def test_parse_requirement_with_marker() -> None:
    dependency = parse_requirement('colorama>=0.4; sys_platform == "win32"')

    assert dependency.name == "colorama"
    assert dependency.marker is not None
    assert "sys_platform" in dependency.marker


def test_parse_direct_url_requirement() -> None:
    dependency = parse_requirement("example-package @ https://example.com/package.whl")

    assert dependency.name == "example-package"
    assert dependency.url == "https://example.com/package.whl"


def test_parse_requirement_rejects_invalid_value() -> None:
    with pytest.raises(
        ConfigurationError,
        match="Invalid dependency declaration",
    ):
        parse_requirement("not a valid !!! requirement")


def test_read_pyproject_returns_configuration(
    tmp_path: Path,
) -> None:
    write_pyproject(
        tmp_path,
        """
[project]
name = "example"
version = "0.1.0"
dependencies = ["pandas>=3.0"]
""",
    )

    configuration = read_pyproject(tmp_path)

    assert configuration["project"]["name"] == "example"


def test_read_pyproject_accepts_file_path(
    tmp_path: Path,
) -> None:
    path = write_pyproject(
        tmp_path,
        """
[project]
name = "example"
version = "0.1.0"
""",
    )

    configuration = read_pyproject(path)

    assert configuration["project"]["name"] == "example"


def test_read_pyproject_rejects_missing_file(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ConfigurationError,
        match="pyproject.toml was not found",
    ):
        read_pyproject(tmp_path)


def test_read_pyproject_rejects_invalid_toml(
    tmp_path: Path,
) -> None:
    write_pyproject(
        tmp_path,
        """
[project
name = "broken"
""",
    )

    with pytest.raises(
        ConfigurationError,
        match="Could not parse",
    ):
        read_pyproject(tmp_path)


def test_load_dependencies_returns_direct_dependencies(
    tmp_path: Path,
) -> None:
    write_pyproject(
        tmp_path,
        """
[project]
name = "example"
version = "0.1.0"
dependencies = [
    "pandas>=3.0",
    "requests[security]>=2.0",
]
""",
    )

    dependencies = load_dependencies(tmp_path)

    assert len(dependencies) == 2
    assert dependencies[0].name == "pandas"
    assert dependencies[1].name == "requests"
    assert dependencies[1].extras == ("security",)


def test_load_dependencies_handles_empty_list(
    tmp_path: Path,
) -> None:
    write_pyproject(
        tmp_path,
        """
[project]
name = "example"
version = "0.1.0"
dependencies = []
""",
    )

    assert load_dependencies(tmp_path) == ()


def test_load_dependencies_handles_missing_dependency_field(
    tmp_path: Path,
) -> None:
    write_pyproject(
        tmp_path,
        """
[project]
name = "example"
version = "0.1.0"
""",
    )

    assert load_dependencies(tmp_path) == ()


def test_load_dependencies_rejects_non_list_value(
    tmp_path: Path,
) -> None:
    write_pyproject(
        tmp_path,
        """
[project]
name = "example"
version = "0.1.0"
dependencies = "pandas"
""",
    )

    with pytest.raises(
        ConfigurationError,
        match="must be a list",
    ):
        load_dependencies(tmp_path)
