#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from playwright.sync_api import BrowserContext, expect

from tests.testlib.playwright.helpers import Keys
from tests.testlib.playwright.pom.login import LoginPage


@pytest.mark.parametrize("snapin_id", [("snapin_container_time"), ("snapin_container_speedometer")])
def test_add_remove_snapin(logged_in_page: LoginPage, snapin_id: str) -> None:
    """add and remove a snapin (aka a sidebar element)"""

    logged_in_page.goto_add_sidebar_element()
    logged_in_page.main_area.locator(f"div.snapinadder:has(div#{snapin_id})").click()
    logged_in_page.main_area.locator(f"div#{snapin_id}").wait_for(state="detached")

    logged_in_page.locator(f"div#check_mk_sidebar >> div#{snapin_id}").wait_for(state="attached")
    logged_in_page.locator(
        f"div#check_mk_sidebar >> div#{snapin_id} >> div.snapin_buttons >> a"
    ).click()
    logged_in_page.locator(f"div#check_mk_sidebar >> div#{snapin_id}").wait_for(state="detached")

    logged_in_page.main_area.locator(f"div#{snapin_id}").wait_for(state="attached")


def test_monitor_searchbar(logged_in_page: LoginPage, context: BrowserContext) -> None:
    """Navigate to the CPU inventory from the monitor searchbar."""

    logged_in_page.main_menu.monitor_searchbar.fill("all hosts")

    expect(logged_in_page.locator("#Monitor")).to_contain_text("All hosts")
    expect(logged_in_page.locator("#Monitor")).to_contain_text("CPU inventory of all hosts")

    logged_in_page.press_keyboard(Keys.ArrowDown)
    logged_in_page.press_keyboard(Keys.ArrowDown)
    logged_in_page.press_keyboard(Keys.Enter)

    logged_in_page.main_area.check_page_title("CPU inventory of all hosts")
