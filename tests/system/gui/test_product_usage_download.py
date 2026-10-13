#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test for downloading product usage data"""

import json
import logging

from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.setup.global_settings import GlobalSettings

logger = logging.getLogger(__name__)


def test_product_usage_download(dashboard_page: MainDashboard) -> None:
    """Test downloading product usage data as JSON file.

    * Open the editor of the 'Product usage analytics' setting
    * Follow its hint to download the usage JSON file
    * Validate the file name and content
    """
    logger.info("Test: Download product usage")

    editor = GlobalSettings(dashboard_page.page).open_editor("Product usage analytics")

    with dashboard_page.page.expect_download() as download_info:
        editor.container.get_by_role("link", name="download the full JSON report").click()

    download = download_info.value

    expected_filename = "checkmk_product_usage.json"
    assert download.suggested_filename == expected_filename, (
        f"Expected filename '{expected_filename}', got '{download.suggested_filename}'"
    )

    download_path = download.path()

    with open(download_path) as f:
        data = json.load(f)

    assert isinstance(data, dict), "Product usage data should be a dictionary"

    assert "id" in data, "Product usage data should contain 'id' key"
    assert "edition" in data, "Product usage data should contain 'edition' key"
    assert "cmk_version" in data, "Product usage data should contain 'cmk_version' key"
    assert "count_hosts" in data, "Product usage data should contain 'count_hosts' key"
    assert "count_services" in data, "Product usage data should contain 'count_services' key"
    assert "checks" in data, "Product usage data should contain 'checks' key"

    logger.info("Product usage data keys: %s", list(data.keys()))
    logger.info("Successfully downloaded and validated product usage file: %s", expected_filename)
