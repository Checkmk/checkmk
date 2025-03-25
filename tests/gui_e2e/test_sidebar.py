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
