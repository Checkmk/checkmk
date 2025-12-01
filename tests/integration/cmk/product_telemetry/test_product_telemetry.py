#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging

import pytest

from tests.testlib.site import Site

logger = logging.getLogger(__name__)

EXPECTED_FOLDER_COUNT = 5
EXPECTED_HOST_COUNT = 3
TELEMETRY_DATA_PATH = "var/check_mk/telemetry"


@pytest.fixture(name="default_cfg", scope="module")
def default_cfg_fixture(site: Site) -> None:
    site.ensure_running()
    for i in range(EXPECTED_FOLDER_COUNT):
        site.openapi.folders.create(f"test_folder_pt{i + 1}")
    for i in range(EXPECTED_HOST_COUNT):
        site.openapi.hosts.create(
            f"test-host-pt{i + 1}",
            attributes={"ipaddress": "127.0.0.1"},
        )
    site.openapi.changes.activate_and_wait_for_completion()


@pytest.mark.usefixtures("default_cfg")
def test_collect_product_telemetry_data_locally(site: Site) -> None:
    """Verify product telemetry data is collected and stored locally without upload."""
    # Execute telemetry collection
    result = site.execute(["cmk-telemetry", "--collection"])
    assert result.wait() == 0, f"Telemetry collection failed: {result.stderr}"
    assert site.is_dir(TELEMETRY_DATA_PATH), f"Telemetry directory not found: {TELEMETRY_DATA_PATH}"

    # Identify telemetry files (JSON and telemetry_id)
    telemetry_files = site.listdir(TELEMETRY_DATA_PATH)
    json_files = [f for f in telemetry_files if f.endswith(".json")]
    assert len(json_files) == 1, f"Expected 1 JSON file, found {len(json_files)}: {json_files}"
    json_file = json_files[0]
    assert "telemetry_id" in telemetry_files, (
        f"telemetry_id file not found. Found: {telemetry_files}"
    )

    # Read contents of files
    telemetry_id_content = site.read_file(f"{TELEMETRY_DATA_PATH}/telemetry_id").strip()
    logger.info(f"Telemetry ID: {telemetry_id_content}")
    json_content = site.read_file(f"{TELEMETRY_DATA_PATH}/{json_file}")
    logger.info(f"Telemetry JSON content: {json_content}")

    # Verify site id is not exposed in telemetry files
    assert site.id not in json_content, (
        f"site.id ({site.id}) should not be present in telemetry data"
    )
    assert site.id not in telemetry_id_content, (
        f"site.id ({site.id}) should not be present in telemetry_id file"
    )

    # Validate JSON structure and counts
    telemetry_data = json.loads(json_content)
    assert "metadata" in telemetry_data
    assert "data" in telemetry_data

    data = telemetry_data["data"]
    assert data["count_hosts"] == EXPECTED_HOST_COUNT
    assert data["count_folders"] == EXPECTED_FOLDER_COUNT
    assert data["edition"] == site.edition.short
    assert data["cmk_version"] == f"Check_MK {site.version.version_data}"

    # Verify the ID in JSON matches the telemetry_id file
    assert data["id"] == telemetry_id_content
