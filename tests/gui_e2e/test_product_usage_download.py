#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test for downloading product usage data"""

import json
import logging

from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.gui_e2e.testlib.playwright.pom.setup.global_settings import GlobalSettings

logger = logging.getLogger(__name__)


def test_product_usage_download(dashboard_page: MainDashboard) -> None:
    """Test downloading product usage data as JSON file.

    * Navigate to Global Settings page
    * Click on Product usage link
    * Download the usage JSON file
    * Validate the file name and content
    """
    logger.info("Test: Download product usage")

    global_settings = GlobalSettings(dashboard_page.page)
    global_settings.search_settings("Product usage analytics")
    global_settings.main_area.locator().get_by_role(
        "link", name="Product usage analytics", exact=True
    ).click()

    dashboard_page.page.wait_for_load_state("domcontentloaded")
    dashboard_page.page.wait_for_load_state("networkidle")

    download_link = global_settings.main_area.locator("a[href*='download_product_usage']")
    download_link.wait_for(state="visible", timeout=10000)

    with dashboard_page.page.expect_download(timeout=30000) as download_info:
        download_link.click()

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

    logger.info(f"Product usage data keys: {list(data.keys())}")
    logger.info(f"Successfully downloaded and validated product usage file: {expected_filename}")
