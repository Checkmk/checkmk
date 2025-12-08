#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib.mock_server import MockEndpoint, MockMethod, MockResponse, MockServer
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

EXPECTED_FOLDER_COUNT = 5
EXPECTED_HOST_COUNT = 3
TELEMETRY_DATA_PATH = "var/check_mk/telemetry"
TELEMETRY_URL_ENV_VAR = "CMK_TELEMETRY_URL"


@pytest.fixture(scope="module")
def default_cfg(site: Site) -> None:
    """Setup site and create resources for product telemetry tests."""
    site.ensure_running()
    for i in range(EXPECTED_FOLDER_COUNT):
        site.openapi.folders.create(f"test_folder_pt{i + 1}")
    for i in range(EXPECTED_HOST_COUNT):
        site.openapi.hosts.create(
            f"test-host-pt{i + 1}",
            attributes={"ipaddress": "127.0.0.1"},
        )
    site.openapi.changes.activate_and_wait_for_completion()


@pytest.fixture(autouse=True)
def cleanup_telemetry_data(site: Site) -> Iterator[None]:
    yield
    # Delete telemetry directory if it exists
    if site.is_dir(TELEMETRY_DATA_PATH):
        site.delete_dir(TELEMETRY_DATA_PATH)


@pytest.fixture
def mock_https_server(site: Site, tmp_path: Path) -> Iterator[MockServer]:
    """Provides a mock HTTPS server with proper SSL certificate configuration.

    This fixture creates a mock HTTPS server with a self-signed certificate and ensures
    the site can successfully verify SSL connections to it. The mock server's certificate
    is added to the site's CA bundle before the test runs, allowing the requests library
    to validate the SSL connection. After the test completes, the CA bundle is restored
    to its original state.
    """
    # Read the current CA bundle content path inside the site
    ca_bundle_path = "var/ssl/ca-certificates.crt"
    original_ca_bundle = site.read_file(ca_bundle_path) if site.file_exists(ca_bundle_path) else ""

    with MockServer(https=True, cert_dir=tmp_path) as mock_server:
        # Read the mock server's self-signed certificate and append it to the site's CA bundle.
        mock_cert = mock_server.cert_file.read_text() if mock_server.cert_file else ""
        site.write_file(ca_bundle_path, original_ca_bundle + "\n" + mock_cert)

        try:
            yield mock_server
        finally:
            # Restore the original CA bundle.
            site.write_file(ca_bundle_path, original_ca_bundle)


def run_telemetry_collection(site: Site) -> None:
    """Run telemetry collection."""
    result = site.execute(["cmk-telemetry", "--collection"])
    assert result.wait() == 0, f"Telemetry collection failed: {result.stderr}"
    assert site.is_dir(TELEMETRY_DATA_PATH), f"Telemetry directory not found: {TELEMETRY_DATA_PATH}"


def get_telemetry_json_files(site: Site) -> list[str]:
    """Return the list of JSON files in the telemetry data directory."""
    files = site.listdir(TELEMETRY_DATA_PATH)
    return [f for f in files if f.endswith(".json")]


def get_telemetry_json_content(site: Site) -> str:
    """Return the single telemetry JSON filename (and assert there is exactly one)."""
    json_files = get_telemetry_json_files(site)
    assert len(json_files) == 1, f"Expected 1 JSON file, found {len(json_files)}: {json_files}"
    json_content = site.read_file(f"{TELEMETRY_DATA_PATH}/{json_files[0]}")
    logger.info(f"Telemetry JSON content: {json_content}")
    return json_content


def run_telemetry_upload(site: Site, mock_url: str) -> None:
    """Set CMK_TELEMETRY_URL to the mock server URL and run telemetry upload."""
    result = site.execute(
        ["env", f"{TELEMETRY_URL_ENV_VAR}={mock_url}", "cmk-telemetry", "--upload"]
    )
    assert result.wait() == 0, f"Telemetry upload failed: {result.stderr}"


def validate_telemetry_request(headers: dict[str, str], body: bytes) -> bool:
    """Validate that the telemetry request contains required metadata and data."""
    data = json.loads(body)
    assert "metadata" in data, "Missing metadata in request"
    assert "data" in data, "Missing data in request"
    assert data["metadata"]["name"] == "telemetry"
    assert data["metadata"]["namespace"] == "checkmk"
    return True


@pytest.mark.usefixtures("default_cfg")
def test_telemetry_collection_writes_one_json_file_and_id_file(site: Site) -> None:
    """Telemetry collection writes exactly one JSON file and one telemetry_id file."""
    run_telemetry_collection(site)

    files = site.listdir(TELEMETRY_DATA_PATH)
    json_files = [f for f in files if f.endswith(".json")]
    assert len(json_files) == 1, f"Expected 1 JSON file, found {len(json_files)}: {json_files}"
    assert "telemetry_id" in files, f"telemetry_id file not found. Found: {files}"


@pytest.mark.usefixtures("default_cfg")
def test_telemetry_id_file_does_not_contain_site_id(site: Site) -> None:
    """telemetry_id file must not contain the site.id."""
    run_telemetry_collection(site)

    telemetry_id = site.read_file(f"{TELEMETRY_DATA_PATH}/telemetry_id").strip()
    logger.info(f"Telemetry ID: {telemetry_id}")
    assert site.id not in telemetry_id, (
        f"site.id ({site.id}) should not be present in telemetry_id file"
    )


@pytest.mark.usefixtures("default_cfg")
def test_telemetry_json_does_not_contain_site_id(site: Site) -> None:
    """Telemetry JSON must not contain the site.id."""
    run_telemetry_collection(site)

    json_content = get_telemetry_json_content(site)
    assert site.id not in json_content, (
        f"site.id ({site.id}) should not be present in telemetry data"
    )


@pytest.mark.usefixtures("default_cfg")
def test_telemetry_json_has_expected_structure(site: Site) -> None:
    """Telemetry JSON has required top-level metadata and data sections."""
    run_telemetry_collection(site)

    json_content = get_telemetry_json_content(site)
    telemetry_data = json.loads(json_content)
    assert "metadata" in telemetry_data
    assert "data" in telemetry_data


@pytest.mark.usefixtures("default_cfg")
def test_telemetry_json_id_matches_telemetry_id_file(site: Site) -> None:
    """Telemetry JSON data.id matches telemetry_id file content."""
    run_telemetry_collection(site)

    json_content = get_telemetry_json_content(site)
    telemetry_data = json.loads(json_content)
    telemetry_id = site.read_file(f"{TELEMETRY_DATA_PATH}/telemetry_id").strip()
    assert telemetry_data["data"]["id"] == telemetry_id


@pytest.mark.usefixtures("default_cfg")
def test_telemetry_json_counts_and_version(site: Site) -> None:
    """Telemetry JSON contains expected counts and version information."""
    run_telemetry_collection(site)

    json_content = get_telemetry_json_content(site)
    telemetry_data = json.loads(json_content)["data"]
    assert telemetry_data["count_hosts"] == EXPECTED_HOST_COUNT
    assert telemetry_data["count_folders"] == EXPECTED_FOLDER_COUNT
    assert telemetry_data["edition"] == site.edition.short
    assert telemetry_data["cmk_version"] == f"{site.version.version_data}"


@pytest.mark.usefixtures("default_cfg")
def test_successful_https_telemetry_data_transmission(
    site: Site, mock_https_server: MockServer
) -> None:
    """Test successful HTTPS transmission of telemetry data."""
    run_telemetry_collection(site)

    mock_https_server.add_endpoint(
        MockEndpoint(method=MockMethod.POST, path="/upload"),
        MockResponse(
            status=200, body=b'{"status": "ok"}', request_validator=validate_telemetry_request
        ),
    )

    run_telemetry_upload(site, f"{mock_https_server.url}/upload")

    # Verify telemetry JSON files were deleted after successful transmission
    json_files = get_telemetry_json_files(site)
    assert len(json_files) == 0, (
        f"Expected 0 JSON files after transmission, found {len(json_files)}: {json_files}"
    )
