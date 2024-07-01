#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from playwright.sync_api import expect

from tests.testlib.playwright.pom.dashboard import Dashboard


def test_dashboard_sanity_check(dashboard_page: Dashboard) -> None:
    for dashlet_title in dashboard_page.default_dashlets_list:
        expect(dashboard_page.dashlet(dashlet_title)).to_be_visible()

    for dropdown_button_name in dashboard_page.dropdown_buttons:
        expect(dashboard_page.dropdown_button(dropdown_button_name)).to_be_visible()

    for icon_title in dashboard_page.icons_list:
        expect(dashboard_page.menu_icon(icon_title)).to_be_visible()

    expect(dashboard_page.dashlet_svg("Host statistics")).to_be_visible()
    expect(dashboard_page.dashlet_svg("Service statistics")).to_be_visible()
