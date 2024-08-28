#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.testlib.playwright.helpers import DropdownListNameToID
from tests.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class HostsDashboard(CmkPage):
    """Represent a base class for 'Linux hosts' and 'Windows hosts' pages."""

    page_title: str = ""

    chart_dashlets: list[str] = []
    table_dashlets: list[str] = []
    plot_dashlets: list[str] = []

    dashlets_list: list[str] = []

    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.monitor_menu(self.page_title).click()
        _url_pattern: str = quote_plus(
            f"dashboard.py?name={self.page_title.split()[0].lower()}_hosts_overview"
        )
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self._validate_page()

    def _validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.dashlet(self.chart_dashlets[0])).to_be_visible()
        expect(self.dashlet(self.table_dashlets[0])).to_be_visible()

    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def dashlet(self, dashlet_title: str) -> Locator:
        return self.main_area.locator(f'div[class*="dashlet "]:has-text("{dashlet_title}")')

    def dashlet_table(self, dashlet_title: str) -> Locator:
        if self.dashlet(dashlet_title).locator("iframe").count() > 0:
            return (
                self.dashlet(dashlet_title).frame_locator("iframe").locator("table[class*='data']")
            )
        return self.dashlet(dashlet_title).locator("table[class*='data']")

    def dashlet_table_rows(self, dashlet_title: str) -> Locator:
        return self.dashlet_table(dashlet_title).locator("tr[class*='data']")

    def dashlet_svg(self, dashlet_title: str) -> Locator:
        return self.dashlet(dashlet_title).locator("svg[class='renderer']")

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

    def total_count(self, dashlet_title: str) -> Locator:
        return self.dashlet(dashlet_title).locator("a[class='count ']")

    def scatterplot(self, dashlet_title: str) -> Locator:
        return self.dashlet(dashlet_title).locator("svg[class='renderer']")

    def wait_for_scatterplot_to_load(self, dashlet_title: str, max_attempts: int = 15) -> None:
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


class LinuxHostsDashboard(HostsDashboard):
    """Represent 'Linux hosts' page.

    To navigate: 'Monitor -> Overview -> Linux hosts'.
    """

    page_title = "Linux hosts"

    table_dashlets = [
        "Top 10: CPU utilization",
        "Top 10: Memory utilization",
        "Top 10: Input bandwidth",
        "Top 10: Output bandwidth",
        "Top 10: Disk utilization",
        "Host information",
        "Filesystems",
    ]
    chart_dashlets = [
        "Host statistics",
        "Service statistics",
    ]
    plot_dashlets = ["Total agent execution time"]

    dashlets_list = table_dashlets + chart_dashlets + plot_dashlets


class WindowsHostsDashboard(HostsDashboard):
    """Represent 'Windows hosts' page.

    To navigate: 'Monitor -> Overview -> Windows hosts'.
    """

    page_title = "Windows hosts"

    table_dashlets = [
        "Top 10: CPU utilization",
        "Top 10: Memory utilization",
        "Top 10: Input bandwidth",
        "Top 10: Output bandwidth",
        "Top 10: Avg. disk write latency",
        "Host information",
        "Filesystems",
    ]
    chart_dashlets = [
        "Host statistics",
        "Service statistics",
    ]
    plot_dashlets = ["Total agent execution time"]

    dashlets_list = table_dashlets + chart_dashlets + plot_dashlets
