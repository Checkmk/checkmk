#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from playwright.sync_api import Locator

from tests.gui_e2e.testlib.playwright.pom.page import MainArea


class ServicesTable:
    """Represents a reusable services table component"""

    def __init__(self, main_area: MainArea) -> None:
        self.main_area = main_area

    def host_services_table(self, host_name: str) -> Locator:
        """Return a locator for a services table corresponding to the host"""
        return self.main_area.locator(f"table.boxlayout:has(td.nobr:has-text('{host_name}'))")

    def service_row(self, host_name: str, service_name: str) -> Locator:
        """Return a locator for a row corresponding to the service."""
        return self.host_services_table(host_name).locator(
            f"tr[class*='data']:has(a:has-text('{service_name}'))"
        )

    def service_state(self, host_name: str, service_name: str) -> Locator:
        return self.service_row(host_name, service_name).locator("td[class*='state']")

    def service_name(self, host_name: str, service_name: str) -> Locator:
        return self.host_services_table(host_name).get_by_role("link", name=service_name)

    def service_icons(self, host_name: str, service_name: str) -> Locator:
        return self.service_row(host_name, service_name).locator("td[class='icons']")

    def service_summary(self, host_name: str, service_name: str) -> Locator:
        return self.service_row(host_name, service_name).locator("td:nth-child(4)")
