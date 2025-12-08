#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
from collections.abc import Iterator

import pytest

from tests.testlib.site import Site

logger = logging.getLogger(__name__)

EXPECTED_FOLDER_COUNT = 5
EXPECTED_HOST_COUNT = 3
TELEMETRY_DATA_PATH = "var/check_mk/telemetry"


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


def run_telemetry_collection(site: Site) -> None:
    """Run telemetry collection."""
    result = site.execute(["cmk-telemetry", "--collection"])
    assert result.wait() == 0, f"Telemetry collection failed: {result.stderr}"
    assert site.is_dir(TELEMETRY_DATA_PATH), f"Telemetry directory not found: {TELEMETRY_DATA_PATH}"


def get_telemetry_json_content(site: Site) -> str:
    """Return the single telemetry JSON filename (and assert there is exactly one)."""
    files = site.listdir(TELEMETRY_DATA_PATH)
    json_files = [f for f in files if f.endswith(".json")]
    assert len(json_files) == 1, f"Expected 1 JSON file, found {len(json_files)}: {json_files}"
    json_content = site.read_file(f"{TELEMETRY_DATA_PATH}/{json_files[0]}")
    logger.info(f"Telemetry JSON content: {json_content}")
    return json_content


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
