#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from playwright.sync_api import Locator

from tests.gui_e2e.testlib.playwright.pom.page import Sidebar


class TacticalOverviewSnapin(Sidebar.Snapin):
    """Represents the 'Tactical Overview' snapin in the sidebar."""

    @property
    def hosts_number(self) -> Locator:
        return self.container.locator("a[href='view.py?view_name=allhosts']")

    @property
    def hosts_unhandled(self) -> Locator:
        return self.container.locator(
            "a[href*='view_name=hostproblems'][href*='is_host_acknowledged=0']"
        )

    @property
    def services_number(self) -> Locator:
        return self.container.locator("a[href='view.py?view_name=allservices']")

    @property
    def services_unhandled(self) -> Locator:
        return self.container.locator(
            "a[href*='view_name=svcproblems'][href*='is_service_acknowledged=0']"
        )

    @property
    def events_number(self) -> Locator:
        return self.container.locator("a[href='view.py?view_name=ec_events']")

    @property
    def events_unhandled(self) -> Locator:
        return self.container.locator("a[href*='view_name=ec_events'][href*='event_phase_open=on']")
