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


class SummarywidgetType(StrEnum):
    """Types of summary widgets."""

    HOST = "Host state summary"
    SERVICE = "Service state summary"


class BaseDashboard(CmkPage):
    """Base class for all dashboard pages.

    This class is not intended to be used directly, but rather as a base class for specific
    dashboard pages. It provides common functionality and properties that are shared across
    different dashboard pages.
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

    def check_selected_dashboard_name(self) -> None:
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
    def dashboard_container(self) -> Locator:
        """Locator property for the dashboard container"""
        return self.main_area.locator("cmk-dashboard")

    @property
    def _menu_header(self) -> Locator:
        """Locator property for top menu of the dashboard"""
        return self.main_area.locator(".dashboard-menu-header")

    @property
    def dashboard_selector(self) -> Locator:
        """Locator property for the dropdown to select the dashboard

        This is the place where dashboard title is checked.
        """
        return self._menu_header.get_by_role("textbox")

    def get_menu_button(self, button_name: str) -> Locator:
        """Get button of the top menu by its name.

        Args:
            button_name: name of the button to get.

        Returns:
            The locator of the button with the given name.
        """
        return self._menu_header.get_by_role("button", name=button_name)

    def get_widget(self, widget_title: str) -> Locator:
        """Get the Locator of the widget with the given title.

        Args:
            widget_title: the title of the widget.

        Returns:
            The locator of the widget with the given title.
        """
        return (
            self.main_area.locator()
            .get_by_label("Widget")
            .filter(has=self.page.get_by_role("heading", name=widget_title))
        )

    def get_widget_table(self, widget_title: str) -> Locator:
        """Get the table inside a widget.

        Args:
            widget_title: the title of the widget.

        Returns:
            The locator of the table inside the widget.
        """
        return self.get_widget(widget_title).locator("table")

    def get_widget_table_rows(self, widget_title: str) -> Locator:
        """Get the rows of the table inside a widget exluding the table heading.

        Args:
            widget_title: the title of the widget.

        Returns:
            The locator of the rows of the table inside the widget.
        """
        return self.get_widget_table(widget_title).locator("tr:not(:first-child)")

    def get_widget_table_column_cells(self, widget_title: str, *, column_index: int) -> Locator:
        """Get the cells that belong to one specific column of the table inside a widget.

        Args:
            widget_title: the title of the widget.
            column_index: the index of the column to get the cells.

        Returns:
            The locator of the cells that belong to the given column of the table
            inside the widget.
        """
        return self.get_widget_table_rows(widget_title).locator(f"> td:nth-child({column_index})")

    def check_widget_is_present(self, widget_title: str) -> None:
        """Check that a specific widget is present on the page.

        Args:
            widget_title: the title of the widget to check.
        """
        expect(
            self.get_widget(widget_title), f"Widget '{widget_title}' is not presented on the page"
        ).to_be_visible()


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
        self.check_selected_dashboard_name()
        expect(self.get_widget("Host statistics")).to_be_visible()
        expect(self.get_menu_button("Filter")).to_be_visible()


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
        self.check_selected_dashboard_name()
        expect(self.get_widget("Host statistics")).to_be_visible()
        expect(self.get_widget("Events of recent 4 hours")).to_be_visible()


# TODO: create Default dashboard POM for admin and non-admin users, see CMK-19521.
