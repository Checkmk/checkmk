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

    dashboard_page.locator(f"div#check_mk_sidebar >> div#{snapin_id}").wait_for(state="attached")
    dashboard_page.locator(
        f"div#check_mk_sidebar >> div#{snapin_id} >> div.snapin_buttons >> a"
    ).click()
    dashboard_page.locator(f"div#check_mk_sidebar >> div#{snapin_id}").wait_for(state="detached")

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
    4. Confirms that the "edit" button in the NagVis snapin is visible and clickable.
    5. Clicks the "edit" button and verifies that the NagVis frame is loaded.
    """

    snapin_id = "snapin_container_nagvis_maps"

    # add nagvis snapin to the sidebar
    dashboard_page.goto_add_sidebar_element()
    dashboard_page.main_area.locator(f"div.snapinadder:has(div#{snapin_id})").click()
    dashboard_page.main_area.locator(f"div#{snapin_id}").wait_for(state="detached")

    # check that the nagvis snapin is visible in the sidebar
    navgis_maps_snapin_container = dashboard_page.locator(
        f"div#check_mk_sidebar >> div#{snapin_id}"
    )
    navgis_maps_snapin_container.wait_for(state="visible")

    # Wait for the loading spinner to disappear
    navgis_maps_snapin_container.locator("div#snapin_nagvis_maps >> div.loading").wait_for(
        state="detached"
    )

    # Check that the nagvis snapin has no error message
    nagvis_maps_error_message = navgis_maps_snapin_container.locator("div.message.error")
    assert not nagvis_maps_error_message.is_visible(), (
        "Nagvis error message is visible, but should not be. "
        f"Error message: '{nagvis_maps_error_message.inner_text()}'"
    )

    # Check that the nagvis snapin edit button is visible and clickable
    nagvis_maps_edit_button = navgis_maps_snapin_container.locator("div.footnotelink >> a")
    assert nagvis_maps_edit_button.is_visible(), "Nagvis 'edit' button is not visible"

    nagvis_maps_edit_button.click()

    # Check that the nagvis edit frame is loaded
    dashboard_page.get_frame_locator("div#content_area >> iframe").locator(
        "div#header >> img[alt='NagVis']"
    ).wait_for(state="visible")
