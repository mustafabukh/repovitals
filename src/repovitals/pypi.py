"""Retrieve and interpret package metadata from the PyPI API."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from packaging.utils import canonicalize_name

from repovitals.cache import read_cached_package, write_cached_package
from repovitals.errors import PackageApiError
from repovitals.models import PackageMetadata

PYPI_API_URL = "https://pypi.org/pypi/{package_name}/json"
DEFAULT_TIMEOUT = 20
USER_AGENT = "RepoVitals/0.1.0"


def parse_datetime(value: str) -> datetime:
    """Parse an ISO 8601 timestamp returned by PyPI."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def find_latest_release(data: dict[str, Any]) -> datetime | None:
    """Return the most recent upload timestamp in PyPI release data."""
    releases = data.get("releases", {})

    if not isinstance(releases, dict):
        return None

    upload_dates = []

    for files in releases.values():
        if not isinstance(files, list):
            continue

        for file_data in files:
            if not isinstance(file_data, dict):
                continue

            timestamp = file_data.get("upload_time_iso_8601")

            if not isinstance(timestamp, str):
                continue

            try:
                upload_dates.append(parse_datetime(timestamp))
            except ValueError:
                continue

    return max(upload_dates, default=None)


def count_releases(data: dict[str, Any]) -> int:
    """Count package versions that contain at least one release file."""
    releases = data.get("releases", {})

    if not isinstance(releases, dict):
        return 0

    return sum(
        1 for files in releases.values() if isinstance(files, list) and len(files) > 0
    )


def find_source_url(data: dict[str, Any]) -> str | None:
    """Find a likely source repository URL in PyPI metadata."""
    info = data.get("info", {})

    if not isinstance(info, dict):
        return None

    project_urls = info.get("project_urls") or {}

    if isinstance(project_urls, dict):
        preferred_names = (
            "source",
            "source code",
            "repository",
            "code",
            "github",
            "homepage",
        )

        normalized_urls = {
            str(name).strip().lower(): url
            for name, url in project_urls.items()
            if isinstance(url, str) and url.strip()
        }

        for preferred_name in preferred_names:
            url = normalized_urls.get(preferred_name)

            if url:
                return url

        for url in normalized_urls.values():
            if "github.com" in url.lower():
                return url

    for field in ("project_url", "home_page"):
        value = info.get(field)

        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def parse_package_metadata(data: dict[str, Any]) -> PackageMetadata:
    """Convert a PyPI API response into structured package metadata."""
    info = data.get("info")

    if not isinstance(info, dict):
        raise PackageApiError("PyPI response is missing package information.")

    name = info.get("name")
    version = info.get("version")

    if not isinstance(name, str) or not name:
        raise PackageApiError("PyPI response is missing the package name.")

    if not isinstance(version, str) or not version:
        raise PackageApiError("PyPI response is missing the package version.")

    summary = info.get("summary")
    requires_python = info.get("requires_python")
    package_url = info.get("package_url")

    if not isinstance(summary, str):
        summary = ""

    if not isinstance(requires_python, str) or not requires_python:
        requires_python = None

    if not isinstance(package_url, str) or not package_url:
        package_url = f"https://pypi.org/project/{canonicalize_name(name)}/"

    return PackageMetadata(
        name=name,
        version=version,
        summary=summary,
        package_url=package_url,
        source_url=find_source_url(data),
        latest_release=find_latest_release(data),
        release_count=count_releases(data),
        requires_python=requires_python,
    )


def download_package_data(
    package_name: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Download raw package metadata from PyPI."""
    url = PYPI_API_URL.format(package_name=canonicalize_name(package_name))

    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
    except requests.RequestException as error:
        raise PackageApiError(
            f"Could not contact PyPI for {package_name!r}: {error}"
        ) from error

    if response.status_code == 404:
        raise PackageApiError(f"Package was not found on PyPI: {package_name}")

    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        raise PackageApiError(
            f"PyPI returned HTTP {response.status_code} for package {package_name!r}."
        ) from error

    try:
        data = response.json()
    except requests.JSONDecodeError as error:
        raise PackageApiError(
            f"PyPI returned invalid JSON for package {package_name!r}."
        ) from error

    if not isinstance(data, dict):
        raise PackageApiError(
            f"PyPI returned unexpected data for package {package_name!r}."
        )

    return data


def load_package_metadata(
    package_name: str,
    *,
    cache_directory: str | Path = ".repovitals-cache",
    offline: bool = False,
    refresh: bool = False,
) -> PackageMetadata:
    """Load package metadata from the cache or PyPI.

    Args:
        package_name: Name of the PyPI package.
        cache_directory: Directory used for cached API responses.
        offline: Use cached data without making a network request.
        refresh: Ignore existing cached data and download fresh data.
    """
    cached_data = None

    if not refresh:
        cached_data = read_cached_package(cache_directory, package_name)

    if cached_data is not None:
        return parse_package_metadata(cached_data)

    if offline:
        raise PackageApiError(
            f"No cached PyPI response is available for {package_name!r}."
        )

    downloaded_data = download_package_data(package_name)
    write_cached_package(cache_directory, package_name, downloaded_data)

    return parse_package_metadata(downloaded_data)
