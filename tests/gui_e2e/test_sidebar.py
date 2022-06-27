#!/usr/bin/env python
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.playwright.helpers import PPage


@pytest.mark.parametrize("snapin_id", [("snapin_container_time"), ("snapin_container_speedometer")])
def test_add_remove_snapin(logged_in_page: PPage, snapin_id: str) -> None:
    """add and remove a snapin (aka a sidebar element)"""

    logged_in_page.goto_add_sidebar_element()
    logged_in_page.main_frame.locator(f"div.snapinadder:has(div#{snapin_id})").click()
    logged_in_page.main_frame.locator(f"div#{snapin_id}").wait_for(state="detached")

    logged_in_page.locator(f"div#check_mk_sidebar >> div#{snapin_id}").wait_for(state="attached")
    logged_in_page.locator(
        f"div#check_mk_sidebar >> div#{snapin_id} >> div.snapin_buttons >> a"
    ).click()
    logged_in_page.locator(f"div#check_mk_sidebar >> div#{snapin_id}").wait_for(state="detached")

    logged_in_page.main_frame.locator(f"div#{snapin_id}").wait_for(state="attached")
