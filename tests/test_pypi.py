"""Tests for PyPI package metadata."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests

from repovitals.errors import PackageApiError
from repovitals.pypi import (
    count_releases,
    download_package_data,
    find_latest_release,
    find_source_url,
    load_package_metadata,
    parse_package_metadata,
)


def sample_pypi_data() -> dict:
    """Return a small response resembling the PyPI API."""
    return {
        "info": {
            "name": "Example-Package",
            "version": "2.0.0",
            "summary": "An example package",
            "package_url": "https://pypi.org/project/example-package/",
            "project_urls": {
                "Documentation": "https://example.com/docs",
                "Source": "https://github.com/example/project",
            },
            "requires_python": ">=3.10",
        },
        "releases": {
            "1.0.0": [{"upload_time_iso_8601": ("2023-01-01T10:00:00.000000Z")}],
            "2.0.0": [{"upload_time_iso_8601": ("2024-06-01T12:30:00.000000Z")}],
            "2.1.0": [],
        },
    }


def test_find_source_url_prefers_source_field() -> None:
    assert find_source_url(sample_pypi_data()) == ("https://github.com/example/project")


def test_find_latest_release_returns_latest_upload() -> None:
    latest = find_latest_release(sample_pypi_data())

    assert latest == datetime(
        2024,
        6,
        1,
        12,
        30,
        tzinfo=UTC,
    )


def test_count_releases_ignores_empty_versions() -> None:
    assert count_releases(sample_pypi_data()) == 2


def test_parse_package_metadata() -> None:
    metadata = parse_package_metadata(sample_pypi_data())

    assert metadata.name == "Example-Package"
    assert metadata.version == "2.0.0"
    assert metadata.summary == "An example package"
    assert metadata.release_count == 2
    assert metadata.source_url == "https://github.com/example/project"
    assert metadata.requires_python == ">=3.10"


class FakeResponse:
    """A minimal HTTP response used by tests."""

    def __init__(
        self,
        data: dict,
        status_code: int = 200,
    ) -> None:
        self.data = data
        self.status_code = status_code

    def json(self) -> dict:
        return self.data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError("HTTP request failed")


def test_download_package_data(monkeypatch) -> None:
    expected = sample_pypi_data()

    def fake_get(url, headers, timeout):
        assert url.endswith("/example-package/json")
        assert "User-Agent" in headers
        assert timeout == 20
        return FakeResponse(expected)

    monkeypatch.setattr(requests, "get", fake_get)

    assert download_package_data("Example_Package") == expected


def test_download_package_data_handles_missing_package(
    monkeypatch,
) -> None:
    def fake_get(url, headers, timeout):
        return FakeResponse({}, status_code=404)

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(PackageApiError, match="not found"):
        download_package_data("missing-package")


def test_load_package_metadata_uses_cache(
    tmp_path: Path,
) -> None:
    from repovitals.cache import write_cached_package

    write_cached_package(
        tmp_path,
        "example-package",
        sample_pypi_data(),
    )

    metadata = load_package_metadata(
        "example-package",
        cache_directory=tmp_path,
        offline=True,
    )

    assert metadata.name == "Example-Package"
    assert metadata.version == "2.0.0"


def test_offline_mode_requires_cached_data(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        PackageApiError,
        match="No cached PyPI response",
    ):
        load_package_metadata(
            "missing",
            cache_directory=tmp_path,
            offline=True,
        )
