#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
from collections.abc import Callable, Generator, Iterator
from http import HTTPStatus
from pathlib import Path

import pytest

from tests.testlib.system.agent_dumps import create_agent_dump_rule
from tests.testlib.system.mock_server import MockEndpoint, MockMethod, MockResponse, MockServer
from tests.testlib.system.site import Site

logger = logging.getLogger(__name__)

EXPECTED_FOLDER_COUNT = 5
EXPECTED_HOST_COUNT = 3
PRODUCT_USAGE_DATA_PATH = "var/check_mk/product_usage"
PRODUCT_USAGE_SITE_ID_PATH = "var/check_mk/product_usage/site_id"
PRODUCT_USAGE_URL_ENV_VAR = "CMK_PRODUCT_USAGE_URL"
PRODUCT_USAGE_COMMAND = "cmk-product-usage"

# The fields that a standalone site with the default configuration sends as null, and why
NULL_ON_A_DEFAULT_SITE = {
    "grafana": "the site is not connected to the Grafana plug-in",
    "site_created_at": "the Cloud trial payload does not collect it yet",
    "sessions": "the Cloud trial payload does not collect it yet",
}


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


AGENT_HOSTS_FOLDER = "product_usage_agents"
# The "check_mk" section of each agent host: the agent version and the operating system.
# The counts cover all hosts of the site, so the OS values are ones no real agent reports.
AGENT_HOST_SECTIONS = {
    "usage-agent-linux": (
        "Version: 2.4.0p12\nAgentOS: usagetestlinux\nOSType: linux\n"
        "OSName: ProductUsageTestOS\nOSVersion: 99.1.7\n"
    ),
    "usage-agent-windows": (
        "Version: 2.3.0p30\nAgentOS: usagetestwindows\nOSType: windows\n"
        "OSName: ProductUsageTestOS Windows\nOSVersion: 98.0.17763\n"
    ),
}


@pytest.fixture
def agent_hosts(site: Site) -> Iterator[None]:
    """Hosts that send a fixed "check_mk" section, discovered and checked once

    The hosts and the rule that feeds them their agent output live in a folder of their
    own, so the other hosts of the site keep their data source. Deleting the folder
    deletes the hosts and the rule as well.
    """
    site.ensure_running()
    site.openapi.folders.create(AGENT_HOSTS_FOLDER)
    dumps_path: Path | None = None
    try:
        _rule_id, dumps_path = create_agent_dump_rule(site, rule_folder=f"/{AGENT_HOSTS_FOLDER}")
        site.makedirs(dumps_path)
        for host_name, section in AGENT_HOST_SECTIONS.items():
            site.write_file(dumps_path / host_name, f"<<<check_mk>>>\n{section}")
            site.openapi.hosts.create(
                host_name, folder=f"/{AGENT_HOSTS_FOLDER}", attributes={"ipaddress": "127.0.0.1"}
            )
        site.openapi.changes.activate_and_wait_for_completion()
        site.openapi.service_discovery.run_bulk_discovery_and_wait_for_completion(
            list(AGENT_HOST_SECTIONS)
        )
        site.openapi.changes.activate_and_wait_for_completion()
        for host_name in AGENT_HOST_SECTIONS:
            site.schedule_check(host_name, "Check_MK")
        yield
    finally:
        if dumps_path is not None:
            for host_name in AGENT_HOST_SECTIONS:
                if site.file_exists(dumps_path / host_name):
                    site.delete_file(dumps_path / host_name)
        site.openapi.folders.delete(f"/{AGENT_HOSTS_FOLDER}")
        site.openapi.changes.activate_and_wait_for_completion()


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
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
    logger.info("Product usage JSON content: %s", json_content)
    return json_content


def run_product_usage_upload(site: Site, mock_url: str) -> None:
    """Set product usage URL to the mock server URL and run product usage upload."""
    result = site.execute(
        ["env", f"{PRODUCT_USAGE_URL_ENV_VAR}={mock_url}", PRODUCT_USAGE_COMMAND, "--upload"]
    )
    assert result.wait() == 0, f"Product usage upload failed: {result.stderr}"


def expected_payload_name(site: Site) -> str:
    """Return the payload name the site sends.

    A fresh Cloud site runs in the trial license state and therefore sends the
    Cloud trial payload instead of the product usage payload.
    """
    if site.edition.is_cloud_edition():
        return "cloud_trial_analytics"
    return "product_usage_analytics"


def make_product_usage_request_validator(
    expected_name: str,
) -> Callable[[dict[str, str], bytes], bool]:
    def validate_product_usage_request(headers: dict[str, str], body: bytes) -> bool:  # noqa: ARG001
        """Validate that the product usage request contains required metadata and data."""
        data = json.loads(body)
        assert "metadata" in data, "Missing metadata in request"
        assert "data" in data, "Missing data in request"
        assert data["metadata"]["name"] == expected_name, (
            f"Expected payload name {expected_name!r}, got {data['metadata']['name']!r}"
        )
        assert data["metadata"]["namespace"] == "checkmk"
        return True

    return validate_product_usage_request


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
    logger.info("Product usage site ID: %s", product_usage_site_id)
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
    assert data["os"] not in ("", "UNKNOWN")


@pytest.mark.usefixtures("default_cfg")
def test_product_usage_json_counts_active_automation_user(site: Site) -> None:
    """The REST API calls of default_cfg are made by an automation user"""
    run_product_usage_collection(site)

    json_content = get_product_usage_json_content(site)
    automation = json.loads(json_content)["data"]["users"]["automation"]
    assert automation["by_role"].get("admin", 0) >= 1
    assert automation["active"]["24h"] >= 1


@pytest.mark.usefixtures("default_cfg")
def test_product_usage_json_reports_standalone_site_languages(site: Site) -> None:
    """A standalone site with the default configuration uses English"""
    run_product_usage_collection(site)

    data = json.loads(get_product_usage_json_content(site))["data"]
    assert data["distributed_monitoring"] == {"is_remote_setup_site": False}
    assert data["languages"]["default_language"] == "en"


@pytest.mark.usefixtures("default_cfg")
def test_product_usage_json_has_a_value_for_every_field_the_site_can_collect(site: Site) -> None:
    """A collector that fails sends its field as null instead of failing the collection

    The collection then succeeds and only the null field shows the failure.
    """
    run_product_usage_collection(site)

    data = json.loads(get_product_usage_json_content(site))["data"]
    may_be_null = set(NULL_ON_A_DEFAULT_SITE)
    if site.edition.is_community_edition():
        may_be_null.add("agent_updater")  # Only the Agent Bakery can count the agent updaters

    null_fields = sorted(name for name, value in data.items() if value is None)
    assert [name for name in null_fields if name not in may_be_null] == [], (
        "A collector failed, see var/log/product_usage_analytics.log"
    )


@pytest.mark.usefixtures("agent_hosts")
def test_product_usage_json_counts_the_agents_by_release_and_os(site: Site) -> None:
    """The agent version is read from the output of the "Check_MK Agent" service"""
    run_product_usage_collection(site)

    agents = json.loads(get_product_usage_json_content(site))["data"]["agents"]
    assert agents["by_version"]["2.4.0"]["usagetestlinux"] == 1
    assert agents["by_version"]["2.3.0"]["usagetestwindows"] == 1
    assert agents["by_os"]["ProductUsageTestOS"] == {"99.1": 1}
    assert agents["by_os"]["ProductUsageTestOS Windows"] == {"98.0": 1}


@pytest.mark.usefixtures("default_cfg")
def test_successful_https_product_usage_data_transmission(
    site: Site, mock_https_server: MockServer
) -> None:
    """Test successful HTTPS transmission of product usage data."""
    run_product_usage_collection(site)

    mock_https_server.add_endpoint(
        MockEndpoint(method=MockMethod.POST, path="/upload"),
        MockResponse(
            status=HTTPStatus.OK,
            body=b'{"status": "ok"}',
            request_validator=make_product_usage_request_validator(expected_payload_name(site)),
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
        MockResponse(
            status=HTTPStatus.INTERNAL_SERVER_ERROR, body=b'{"error": "Internal server error"}'
        ),
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


@pytest.mark.skip_if_not_edition("cloud")
@pytest.mark.usefixtures("default_cfg")
def test_cloud_trial_payload_counts_hosts_with_default_services_only(site: Site) -> None:
    """A Cloud trial site sends the count of hosts with default services only."""
    run_product_usage_collection(site)

    data = json.loads(get_product_usage_json_content(site))["data"]

    assert data["count_hosts_default_services_only"] == EXPECTED_HOST_COUNT, (
        "Each test host has only the default services. A null count means that the collection"
        " failed, see var/log/product_usage_analytics.log"
    )


@pytest.mark.skip_if_not_edition("cloud")
@pytest.mark.usefixtures("default_cfg")
def test_cloud_trial_payload_carries_the_site_creation_time(site: Site) -> None:
    """The Cloud edition config of a test site has no creation time from the platform, so the
    site sends the time when OMD wrote its instance ID."""
    run_product_usage_collection(site)

    data = json.loads(get_product_usage_json_content(site))["data"]

    assert data["site_created_at"] == site.file_timestamp_ms("etc/omd/instance_id") // 1000, (
        "A null time means that the collection failed, see var/log/product_usage_analytics.log"
    )
