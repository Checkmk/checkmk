#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.helpers import Keys
from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard


@pytest.mark.parametrize("snapin_id", [("snapin_container_time"), ("snapin_container_speedometer")])
def test_add_remove_snapin(dashboard_page: Dashboard, snapin_id: str) -> None:
    """add and remove a snapin (aka a sidebar element)"""

    dashboard_page.goto_add_sidebar_element()
    dashboard_page.main_area.locator(f"div.snapinadder:has(div#{snapin_id})").click()
    dashboard_page.main_area.locator(f"div#{snapin_id}").wait_for(state="detached")

    snapin = dashboard_page.sidebar.snapin(snapin_id)

    snapin.container.wait_for(state="attached")
    snapin.remove_from_sidebar()

    dashboard_page.main_area.locator(f"div#{snapin_id}").wait_for(state="attached")


def test_monitor_searchbar(dashboard_page: Dashboard) -> None:
    """Navigate to the CPU inventory from the monitor searchbar."""

    dashboard_page.main_menu.monitor_searchbar.fill("all hosts")

    expect(dashboard_page.locator("#Monitor")).to_contain_text("All hosts")
    expect(dashboard_page.locator("#Monitor")).to_contain_text("CPU inventory of all hosts")

    dashboard_page.press_keyboard(Keys.ArrowDown)
    dashboard_page.press_keyboard(Keys.ArrowDown)
    dashboard_page.press_keyboard(Keys.Enter)

    dashboard_page.main_area.check_page_title("CPU inventory of all hosts")


def test_add_nagvis_snapin(dashboard_page: Dashboard) -> None:
    """Tests the addition of the NagVis snapin to the sidebar and verifies its functionality.

    This test performs the following steps:
    1. Adds the NagVis snapin to the sidebar.
    2. Verifies that the NagVis snapin is visible in the sidebar.
    3. Ensures that no error message is displayed in the NagVis snapin.
    4. Confirms that the "Edit" button in the NagVis snapin is visible and clickable.
    5. Clicks the "Edit" button and verifies that the NagVis frame is loaded.
    6. Cleans up by removing the NagVis snapin from the sidebar.
    7. Verifies that the NagVis snapin is no longer visible in the sidebar.
    """

    snapin_id = "snapin_container_nagvis_maps"

    # add nagvis snapin to the sidebar
    dashboard_page.goto_add_sidebar_element()
    dashboard_page.main_area.locator(f"div.snapinadder:has(div#{snapin_id})").click()
    dashboard_page.main_area.locator(f"div#{snapin_id}").wait_for(state="detached")

    # check that the nagvis snapin is visible in the sidebar
    snapin = dashboard_page.sidebar.snapin(snapin_id)
    snapin.container.wait_for(state="visible")

    # Wait for the loading spinner to disappear
    snapin.loading_spinner.wait_for(state="detached")

    # Check that the nagvis snapin has no error message
    expect(
        snapin.error_message, message="Nagvis error message is visible, but should not be"
    ).not_to_be_visible()

    # Check that the nagvis snapin edit button is visible and clickable
    nagvis_maps_edit_button = snapin.get_button("Edit")
    expect(nagvis_maps_edit_button, message="Nagvis 'Edit' button is not visible").to_be_visible()
    nagvis_maps_edit_button.click()

    # Check that the nagvis edit frame is loaded
    dashboard_page.get_frame_locator("div#content_area >> iframe").locator(
        "div#header >> img[alt='NagVis']"
    ).wait_for(state="visible")

    dashboard_page.goto_add_sidebar_element()
    snapin.remove_from_sidebar()
    dashboard_page.main_area.locator(f"div#{snapin_id}").wait_for(state="attached")
