"""Tests for the JSON response cache."""

from pathlib import Path

from repovitals.cache import (
    package_cache_path,
    read_cached_package,
    write_cached_package,
)


def test_package_cache_path_normalizes_name(
    tmp_path: Path,
) -> None:
    path = package_cache_path(tmp_path, "Example_Package")

    assert path == tmp_path / "pypi" / "example-package.json"


def test_read_cached_package_returns_none_for_missing_file(
    tmp_path: Path,
) -> None:
    assert read_cached_package(tmp_path, "missing") is None


def test_write_and_read_cached_package(
    tmp_path: Path,
) -> None:
    data = {
        "info": {
            "name": "example",
            "version": "1.0.0",
        }
    }

    path = write_cached_package(tmp_path, "example", data)
    loaded = read_cached_package(tmp_path, "example")

    assert path.exists()
    assert loaded == data
