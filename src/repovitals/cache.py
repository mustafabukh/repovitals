"""File-based JSON caching for external API responses."""

import json
from pathlib import Path
from typing import Any

from packaging.utils import canonicalize_name

from repovitals.errors import CacheError


def package_cache_path(
    cache_directory: str | Path,
    package_name: str,
) -> Path:
    """Return the cache-file path for a package."""
    directory = Path(cache_directory).expanduser()
    filename = f"{canonicalize_name(package_name)}.json"
    return directory / "pypi" / filename


def read_cached_package(
    cache_directory: str | Path,
    package_name: str,
) -> dict[str, Any] | None:
    """Read cached PyPI data, returning ``None`` on a cache miss."""
    path = package_cache_path(cache_directory, package_name)

    if not path.exists():
        return None

    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise CacheError(f"Could not read cache file {path}: {error}") from error

    if not isinstance(data, dict):
        raise CacheError(f"Cache file does not contain an object: {path}")

    return data


def write_cached_package(
    cache_directory: str | Path,
    package_name: str,
    data: dict[str, Any],
) -> Path:
    """Write PyPI data to the package cache."""
    path = package_cache_path(cache_directory, package_name)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.write("\n")
    except OSError as error:
        raise CacheError(f"Could not write cache file {path}: {error}") from error

    return path
