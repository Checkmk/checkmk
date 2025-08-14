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


class BaseDashboard(CmkPage):
    """Base class for all dashboard pages.

    This class is not intended to be used directly, but rather as a base class for specific dashboard pages.
    It provides common functionality and properties that are shared across different dashboard pages.
    """

    dropdown_buttons: list[str] = ["Dashboard", "Add", "Dashboards", "Display", "Help"]

    @override
    def navigate(self) -> None:
        raise NotImplementedError("Subclasses must implement the navigate method.")

    @override
    def validate_page(self) -> None:
        raise NotImplementedError("Subclasses must implement the validate_page method.")

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        mapping = DropdownListNameToID()
        setattr(mapping, "Dashboard", "menu_dashboard")
        setattr(mapping, "Add", "menu_add_dashlets")
        setattr(mapping, "Dashboards", "menu_dashboards")
        return mapping

    @property
    def enter_layout_mode_icon(self) -> Locator:
        return self.main_area.locator().get_by_role("link", name="Enter layout mode")

    @property
    def delete_confirmation_window(self) -> Locator:
        return self.main_area.locator("div[class*='confirm_popup']")

    @property
    def delete_confirmation_button(self) -> Locator:
        return self.delete_confirmation_window.get_by_role("button", name="Yes")

    def menu_icon(self, icon_title: str) -> Locator:
        return self.main_area.locator("table#page_menu_bar").get_by_title(icon_title)

    def dashlet(self, dashlet_name: str) -> Locator:
        return self.main_area.locator(f"div[class*='dashlet ']:has(:text-is('{dashlet_name}'))")

    def total_count(self, dashlet_title: str) -> Locator:
        return self.dashlet(dashlet_title).locator("a[class='count ']")

    def dashlet_svg(self, dashlet_name: str) -> Locator:
        return self.dashlet(dashlet_name).locator("svg")

    def scatterplot(self, dashlet_title: str) -> Locator:
        return self.dashlet(dashlet_title).locator("svg[class='renderer']")

    def dashlet_table(self, dashlet_title: str) -> Locator:
        if self.dashlet(dashlet_title).locator("iframe").count() > 0:
            return (
                self.dashlet(dashlet_title).frame_locator("iframe").locator("table[class*='data']")
            )
        return self.dashlet(dashlet_title).locator("table[class*='data']")

    def dashlet_table_rows(self, dashlet_title: str) -> Locator:
        return self.dashlet_table(dashlet_title).locator("tr[class*='data']")

    def _hexagon_chart(self, dashlet_title: str, status: str) -> Locator:
        return self.dashlet(dashlet_title).locator(f"path[class='hexagon {status}']")

    def check_hexagon_chart_is_not_empty(self, dashlet_title: str) -> None:
        statuses = ["ok", "downtime", "unknown", "critical"]
        for status in statuses:
            try:
                expect(self._hexagon_chart(dashlet_title, status)).to_be_visible(timeout=3000)
                return
            except AssertionError:
                continue
        raise AssertionError(f"None of the hexagon charts in dashlet '{dashlet_title}' are visible")

    def wait_for_scatterplot_to_load(self, dashlet_title: str, max_attempts: int = 30) -> None:
        """Wait for scatter plot to be visible on the page.

        When using agent dumps, the scatter plot takes some time to load.
        """
        logger.info("Wait for scatterplot '%s' to load", dashlet_title)
        wait_time = 5
        for _ in range(max_attempts):
            try:
                expect(self.scatterplot(dashlet_title)).to_be_visible(timeout=wait_time * 1000)
            except AssertionError:
                self.page.reload()
            else:
                return
        raise AssertionError(
            f"Scatterplot '{dashlet_title}' is not visible on the page after "
            f"{max_attempts * wait_time} seconds"
        )

    def edit_dashlet_properties_button(self, dashlet_title: str) -> Locator:
        return self.dashlet(dashlet_title).get_by_title("Edit properties of this element")

    def delete_dashlet_button(self, dashlet_title: str) -> Locator:
        return self.dashlet(dashlet_title).get_by_title("Delete this element")

    def enter_layout_mode(self) -> None:
        if self.enter_layout_mode_icon.is_visible():
            self.enter_layout_mode_icon.click()
        else:
            self.main_area.click_item_in_dropdown_list("Dashboard", "Clone built-in dashboard")
        self.page.wait_for_load_state("load")


class Dashboard(BaseDashboard):
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
        self.main_area.check_page_title(self.page_title)
        expect(self.dashlet("Host statistics")).to_be_visible()
        expect(self.dashlet("Events of recent 4 hours")).to_be_visible()


# TODO: create Default dashboard POM for admin and non-admin users, see CMK-19521.
