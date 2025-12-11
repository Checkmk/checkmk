#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard import BaseDashboard

logger = logging.getLogger(__name__)


class HostsDashboard(BaseDashboard):
    """Represent a base class for 'Linux hosts' and 'Windows hosts' pages."""

    chart_widgets: list[str] = []
    table_widgets: list[str] = []
    plot_widgets: list[str] = []

    widgets_list: list[str] = []

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.monitor_menu(self.page_title).click()
        _url_pattern: str = quote_plus(
            f"dashboard.py?name={self.page_title.split()[0].lower()}_hosts_overview"
        )
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.check_selected_dashboard_name()
        expect(
            self.main_area.locator("div#dashboard"),
            message=f"Dashboard '{self.page_title}' is not loaded",
        ).to_be_visible()


class LinuxHostsDashboard(HostsDashboard):
    """Represent 'Linux hosts' page.

    To navigate: 'Monitor -> Overview -> Linux hosts'.
    """

    page_title = "Linux hosts"

    table_widgets = [
        "Top 10: CPU utilization",
        "Top 10: Memory utilization",
        "Top 10: Input bandwidth",
        "Top 10: Output bandwidth",
        "Top 10: Disk utilization",
        "Host information",
        "Filesystems",
    ]
    chart_widgets = [
        "Host statistics",
        "Service statistics",
    ]
    plot_widgets = ["Total agent execution time"]

    widgets_list = table_widgets + chart_widgets + plot_widgets


class WindowsHostsDashboard(HostsDashboard):
    """Represent 'Windows hosts' page.

    To navigate: 'Monitor -> Overview -> Windows hosts'.
    """

    page_title = "Windows hosts"

    table_widgets = [
        "Top 10: CPU utilization (Windows)",
        "Top 10: Memory utilization",
        "Top 10: Input bandwidth",
        "Top 10: Output bandwidth",
        "Top 10: Avg. disk write latency",
        "Host information",
        "Filesystems",
    ]
    chart_widgets = [
        "Host statistics",
        "Service statistics",
    ]
    plot_widgets = ["Total agent execution time"]

    widgets_list = table_widgets + chart_widgets + plot_widgets
