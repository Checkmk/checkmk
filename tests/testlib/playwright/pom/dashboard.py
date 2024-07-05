#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re

from playwright.sync_api import expect, Locator, Page

from tests.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class Dashboard(CmkPage):
    """Represent the page `Main dashboard`."""

    page_title: str = "Main dashboard"

    default_dashlets_list: list[str] = [
        "Host statistics",
        "Service statistics",
        "Problem notifications",
        "Host overview",
        "Total host problems",
        "Total service problems",
        "Percentage of total service problems",
        "Top alerters (last 7 days)",
    ]

    icons_list: list[str] = [
        "Main dashboard",
        "Problem dashboard",
        "Checkmk dashboard",
        "Filter",
    ]

    dropdown_buttons: list[str] = ["Dashboard", "Add", "Dashboards", "Display", "Help"]

    def __init__(self, page: Page, navigate_to_page: bool = True) -> None:
        super().__init__(page, navigate_to_page)

    def navigate(self) -> None:
        logger.info("Navigate to 'Main dashboard' page")
        self.main_menu.main_page.click()
        self.page.wait_for_url(url=re.compile("dashboard.py$"), wait_until="load")
        self._validate_page()

    def _validate_page(self) -> None:
        logger.info("Validate that current page is 'Main dashboard' page")
        self.main_area.check_page_title(self.page_title)
        expect(self.dashlet("Host statistics")).to_be_visible()
        expect(self.menu_icon("Filter")).to_be_visible()

    def menu_icon(self, icon_title: str) -> Locator:
        return self.main_area.locator().get_by_title(icon_title)

    def dashlet(self, dashlet_name: str) -> Locator:
        return self.main_area.locator(
            f'div[class*="dashlet "]:has(text:text-is("{dashlet_name}")), '
            f'div[class*="dashlet "]:has(a:text-is("{dashlet_name}"))'
        )

    def dashlet_svg(self, dashlet_name: str) -> Locator:
        return self.dashlet(dashlet_name).locator("svg")
