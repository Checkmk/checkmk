#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from enum import StrEnum
from re import Pattern
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class SummaryDashletType(StrEnum):
    """Types of summary dashlets."""

    HOST = "Host state summary"
    SERVICE = "Service state summary"


class BaseDashboard(CmkPage):
    """Base class for all dashboard pages.

    This class is not intended to be used directly, but rather as a base class for specific dashboard pages.
    It provides common functionality and properties that are shared across different dashboard pages.
    """

    page_title: str

    @override
    def navigate(self) -> None:
        raise NotImplementedError("Subclasses must implement the navigate method.")

    @override
    def validate_page(self) -> None:
        raise NotImplementedError("Subclasses must implement the validate_page method.")

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def check_dashboard_selector_placeholder(self) -> None:
        """Check that the dashboard selector has the expected placeholder text."""
        expect(
            self.dashboard_selector,
            message=(
                "The dashboard selector does not contain the expected dashboard name."
                f" Expected: '{self.page_title}';"
                f" actual value: '{self.dashboard_selector.get_attribute('placeholder')}'"
            ),
        ).to_have_attribute("placeholder", self.page_title)

    @property
    def _menu_header(self) -> Locator:
        return self.main_area.locator(".dashboard-menu-header")

    @property
    def dashboard_selector(self) -> Locator:
        return self._menu_header.get_by_role("textbox")

    def menu_button(self, button_name: str) -> Locator:
        return self._menu_header.get_by_role("button", name=button_name)

    def widget(self, dashlet_name: str) -> Locator:
        return self.main_area.locator(
            f"div.db-relative-grid-frame:has(:text-is('{dashlet_name}'))"
        )  # To replace with data attribute when available


class MainDashboard(BaseDashboard):
    """Represent the page `Main dashboard`."""

    page_title: str = "Main dashboard"

    default_widget_list: list[str] = [
        "Host statistics",
        "Service statistics",
        "Problem notifications",
        "Host overview",
        "Total host problems",
        "Total service problems",
        "Percentage of total service problems",
        "Top alerters (last 7 days)",
    ]

    header_buttons = (
        "Filter",
        "Settings",
        "Edit widgets",
    )

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Main dashboard' page")
        self.main_menu.monitor_menu("Main dashboard").click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("dashboard.py?name=main")), wait_until="load"
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Main dashboard' page")
        self.check_dashboard_selector_placeholder()
        expect(self.widget("Host statistics")).to_be_visible()
        expect(self.menu_button("Filter")).to_be_visible()


class DashboardMobile(BaseDashboard):
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
    def get_link(self, name: str | Pattern[str], exact: bool = True) -> Locator:
        return self.page.get_by_role(role="link", name=name, exact=exact)

    @property
    def classical_web_gui(self) -> Locator:
        return self.get_link(r"Classical web GUI")

    @property
    def logout(self) -> Locator:
        return self.get_link("Logout")


class ProblemDashboard(BaseDashboard):
    """Represent the page `Problem dashboard`.

    `Problem dashboard` is a default dashboard page for cmk monitoring user.
    """

    page_title: str = "Problem dashboard"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.monitor_menu(self.page_title).click()
        url = quote_plus("dashboard.py?name=problems")
        self.page.wait_for_url(url=re.compile(url), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.check_dashboard_selector_placeholder()
        expect(self.widget("Host statistics")).to_be_visible()
        expect(self.widget("Events of recent 4 hours")).to_be_visible()


# TODO: create Default dashboard POM for admin and non-admin users, see CMK-19521.
