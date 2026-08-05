#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
from collections.abc import Generator, Iterator
from pathlib import Path

import pytest

from tests.testlib.mock_server import MockEndpoint, MockMethod, MockResponse, MockServer
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

EXPECTED_FOLDER_COUNT = 5
EXPECTED_HOST_COUNT = 3
PRODUCT_USAGE_DATA_PATH = "var/check_mk/product_usage"
PRODUCT_USAGE_SITE_ID_PATH = "var/check_mk/product_usage/site_id"
PRODUCT_USAGE_URL_ENV_VAR = "CMK_PRODUCT_USAGE_URL"
PRODUCT_USAGE_COMMAND = "cmk-product-usage"


@pytest.fixture(scope="module")
def default_cfg(site: Site) -> Generator[None]:
    """Setup site and create resources for product usage tests."""
    site.ensure_running()
    for i in range(EXPECTED_FOLDER_COUNT):
        site.openapi.folders.create(f"test_folder_pt{i + 1}")
    for i in range(EXPECTED_HOST_COUNT):
        site.openapi.hosts.create(
            f"test-host-pt{i + 1}",
            attributes={"ipaddress": "127.0.0.1"},
        )
    site.openapi.changes.activate_and_wait_for_completion()
    try:
        yield
    finally:
        for i in range(EXPECTED_HOST_COUNT):
            site.openapi.hosts.delete(f"test-host-pt{i + 1}")
        for i in range(EXPECTED_FOLDER_COUNT):
            site.openapi.folders.delete(f"/test_folder_pt{i + 1}")
        site.openapi.changes.activate_and_wait_for_completion()


@pytest.fixture(autouse=True)
def cleanup_product_usage_data(site: Site) -> Iterator[None]:
    yield
    # Delete product usage directory if it exists
    if site.is_dir(PRODUCT_USAGE_DATA_PATH):
        site.delete_dir(PRODUCT_USAGE_DATA_PATH)


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


def run_product_usage_collection(site: Site) -> None:
    """Run product usage collection."""
    result = site.execute([PRODUCT_USAGE_COMMAND, "--collection"])
    assert result.wait() == 0, f"Product usage collection failed: {result.stderr}"
    assert site.is_dir(PRODUCT_USAGE_DATA_PATH), (
        f"Product usage directory not found: {PRODUCT_USAGE_DATA_PATH}"
    )


def get_product_usage_json_files(site: Site) -> list[str]:
    """Return the list of JSON files in the product usage data directory."""
    files = site.listdir(PRODUCT_USAGE_DATA_PATH)
    return [f for f in files if f.endswith(".json")]


def get_product_usage_json_content(site: Site) -> str:
    """Return the single product usage JSON filename (and assert there is exactly one)."""
    json_files = get_product_usage_json_files(site)
    assert len(json_files) == 1, f"Expected 1 JSON file, found {len(json_files)}: {json_files}"
    json_content = site.read_file(f"{PRODUCT_USAGE_DATA_PATH}/{json_files[0]}")
    logger.info(f"Product usage JSON content: {json_content}")
    return json_content


def run_product_usage_upload(site: Site, mock_url: str) -> None:
    """Set product usage URL to the mock server URL and run product usage upload."""
    result = site.execute(
        ["env", f"{PRODUCT_USAGE_URL_ENV_VAR}={mock_url}", PRODUCT_USAGE_COMMAND, "--upload"]
    )
    assert result.wait() == 0, f"Product usage upload failed: {result.stderr}"


def validate_product_usage_request(headers: dict[str, str], body: bytes) -> bool:
    """Validate that the product usage request contains required metadata and data."""
    data = json.loads(body)
    assert "metadata" in data, "Missing metadata in request"
    assert "data" in data, "Missing data in request"
    assert data["metadata"]["name"] == "product_usage_analytics"
    assert data["metadata"]["namespace"] == "checkmk"
    return True


@pytest.mark.usefixtures("default_cfg")
def test_product_usage_collection_writes_one_json_file_and_id_file(site: Site) -> None:
    """Product usage collection writes exactly one JSON file and one site ID file."""
    run_product_usage_collection(site)

    files = site.listdir(PRODUCT_USAGE_DATA_PATH)
    json_files = [f for f in files if f.endswith(".json")]
    assert len(json_files) == 1, f"Expected 1 JSON file, found {len(json_files)}: {json_files}"
    assert "site_id" in files, f"Product usage site ID file not found. Found: {files}"


@pytest.mark.usefixtures("default_cfg")
def test_product_usage_id_file_does_not_contain_site_id(site: Site) -> None:
    """Product usage site ID file must not contain the license site ID."""
    run_product_usage_collection(site)

    product_usage_site_id = site.read_file(PRODUCT_USAGE_SITE_ID_PATH).strip()
    logger.info(f"Product usage site ID: {product_usage_site_id}")
    assert site.id not in product_usage_site_id, (
        f"site.id ({site.id}) should not be present in the product usage site ID file"
    )


@pytest.mark.usefixtures("default_cfg")
def test_product_usage_json_does_not_contain_site_id(site: Site) -> None:
    """Product usage JSON must not contain the site.id."""
    run_product_usage_collection(site)

    json_content = get_product_usage_json_content(site)
    assert site.id not in json_content, (
        f"site.id ({site.id}) should not be present in product usage data"
    )


@pytest.mark.usefixtures("default_cfg")
def test_product_usage_json_has_expected_structure(site: Site) -> None:
    """Product usage JSON has required top-level metadata and data sections."""
    run_product_usage_collection(site)

    json_content = get_product_usage_json_content(site)
    data = json.loads(json_content)
    assert "metadata" in data
    assert "data" in data


@pytest.mark.usefixtures("default_cfg")
def test_product_usage_json_id_matches_product_usage_site_id_file(site: Site) -> None:
    """Product usage JSON data.id matches product usage site ID file content."""
    run_product_usage_collection(site)

    json_content = get_product_usage_json_content(site)
    data = json.loads(json_content)
    site_id = site.read_file(PRODUCT_USAGE_SITE_ID_PATH).strip()
    assert data["data"]["id"] == site_id


@pytest.mark.usefixtures("default_cfg")
def test_product_usage_json_counts_and_version(site: Site) -> None:
    """Product usage JSON contains expected counts and version information."""
    run_product_usage_collection(site)

    json_content = get_product_usage_json_content(site)
    data = json.loads(json_content)["data"]
    assert data["count_hosts"] == EXPECTED_HOST_COUNT
    assert data["count_folders"] == EXPECTED_FOLDER_COUNT
    assert data["edition"] == site.edition.short
    assert data["cmk_version"] == f"{site.version.version_data}"


@pytest.mark.usefixtures("default_cfg")
def test_successful_https_product_usage_data_transmission(
    site: Site, mock_https_server: MockServer
) -> None:
    """Test successful HTTPS transmission of product usage data."""
    run_product_usage_collection(site)

    mock_https_server.add_endpoint(
        MockEndpoint(method=MockMethod.POST, path="/upload"),
        MockResponse(
            status=200, body=b'{"status": "ok"}', request_validator=validate_product_usage_request
        ),
    )

    run_product_usage_upload(site, f"{mock_https_server.url}/upload")

    # Verify product usage JSON files were deleted after successful transmission
    json_files = get_product_usage_json_files(site)
    assert len(json_files) == 0, (
        f"Expected 0 JSON files after transmission, found {len(json_files)}: {json_files}"
    )


@pytest.mark.usefixtures("default_cfg")
def test_unsuccessful_https_product_usage_data_transmission(
    site: Site, mock_https_server: MockServer
) -> None:
    """Test that failed HTTPS transmission keeps product usage files."""
    run_product_usage_collection(site)

    # Get the JSON files before transmission
    json_files_before = get_product_usage_json_files(site)
    assert len(json_files_before) == 1, (
        f"Expected 1 JSON file before transmission, found {len(json_files_before)}"
    )

    mock_https_server.add_endpoint(
        MockEndpoint(method=MockMethod.POST, path="/upload"),
        MockResponse(status=500, body=b'{"error": "Internal server error"}'),
    )

    run_product_usage_upload(site, f"{mock_https_server.url}/upload")

    # Verify product usage JSON files were NOT deleted after failed transmission
    json_files_after = get_product_usage_json_files(site)
    assert len(json_files_after) == 1, (
        f"Expected 1 JSON file after failed transmission, found {len(json_files_after)}"
    )
    assert json_files_before[0] == json_files_after[0], (
        "JSON file should be the same after failed transmission"
    )
