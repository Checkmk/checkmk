#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test for downloading product usage analytics data"""

import json
import logging

from tests.testlib.playwright.pom.login import LoginPage

logger = logging.getLogger(__name__)


def test_product_usage_download(logged_in_page: LoginPage) -> None:
    """Test downloading product usage analytics data as JSON file.

    * Navigate to Global Settings page
    * Click on Product usage analytics link
    * Download the product usage JSON file
    * Validate the file name and content
    """
    logger.info("Test: Download product usage analytics")

    logged_in_page.main_menu.setup_searchbar.fill("Product usage analytics")
    logged_in_page.page.get_by_role("link", name="Product usage analytics", exact=True).click()

    logged_in_page.page.wait_for_load_state("domcontentloaded")
    logged_in_page.page.wait_for_load_state("networkidle")

    download_link = logged_in_page.main_area.locator("a[href*='download_product_usage']")
    download_link.wait_for(state="visible", timeout=10000)

    with logged_in_page.page.expect_download(timeout=30000) as download_info:
        download_link.click()

    download = download_info.value

    expected_filename = "checkmk_product_usage.json"
    assert (
        download.suggested_filename == expected_filename
    ), f"Expected filename '{expected_filename}', got '{download.suggested_filename}'"

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
