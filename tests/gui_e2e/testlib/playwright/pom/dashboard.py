#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from re import Pattern
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

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

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Main dashboard' page")
        self.main_menu.monitor_menu("Main dashboard").click()
        self.page.wait_for_url(
            url=re.compile(f"{quote_plus('dashboard.py?name=main')}$"), wait_until="load"
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Main dashboard' page")
        self.main_area.check_page_title(self.page_title)
        expect(self.dashlet("Host statistics")).to_be_visible()
        expect(self.menu_icon("Filter")).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def menu_icon(self, icon_title: str) -> Locator:
        return self.main_area.locator().get_by_title(icon_title)

    def dashlet(self, dashlet_name: str) -> Locator:
        return self.main_area.locator(
            f'div[class*="dashlet "]:has(text:text-is("{dashlet_name}")), '
            f'div[class*="dashlet "]:has(a:text-is("{dashlet_name}"))'
        )

    def dashlet_svg(self, dashlet_name: str) -> Locator:
        return self.dashlet(dashlet_name).locator("svg")


class DashboardMobile(CmkPage):
    page_title: str = r"Checkmk Mobile"

    links: list[str] = [
        r"Host Search",
        r"Service Search",
        r"Host problems (all)",
        r"Host problems (unhandled)",
        r"Service problems (all)",
        r"Service problems (unhandled)",
        # "Events" - TODO: confirm why there are two Events.
        r"Classical web GUI",
        "History",
        "Logout",
    ]

    @override
    def navigate(self) -> None:
        """TODO: add navigation"""

    @override
    def validate_page(self) -> None:
        expect(self.page.get_by_role(role="heading", name=self.page_title)).to_have_count(1)
        expect(self.classical_web_gui).to_be_visible()
        expect(self.logout).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @override
    def get_link(self, name: str | Pattern[str], exact: bool = True) -> Locator:
        return self.page.get_by_role(role="link", name=name, exact=exact)

    @property
    def classical_web_gui(self) -> Locator:
        return self.get_link(r"Classical web GUI")

    @property
    def logout(self) -> Locator:
        return self.get_link("Logout")


class ProblemDashboard(CmkPage):
    """Represent the page `Problem dashboard`.

    `Problem dashboard` is a default dashboard page for cmk monitoring user.
    #TODO: create a common base class for 'Main dashboard' and 'Problem dashboard', see CMK-19521
    """

    page_title: str = "Problem dashboard"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.main_page.click()
        self.page.wait_for_url(url=re.compile("dashboard.py$"), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.dashlet("Host statistics")).to_be_visible()
        expect(self.dashlet("Events of recent 4 hours")).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def dashlet(self, dashlet_name: str) -> Locator:
        return self.main_area.locator(
            f'div[class*="dashlet "]:has(text:text-is("{dashlet_name}")), '
            f'div[class*="dashlet "]:has(a:text-is("{dashlet_name}"))'
        )
