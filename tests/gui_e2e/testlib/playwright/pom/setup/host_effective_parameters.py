#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.host_details import HostDetails
from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.hosts import SetupHost

logger = logging.getLogger(__name__)


class HostEffectiveParameters(CmkPage):
    """Represent the 'Effective parameters of <host name>' page.

    To navigate: `Setup -> Hosts -> <Host name> ->
    View the rule based effective parameters of the host`.
    """

    sections: list[str] = [
        r"Host information",
        r"Access to agents",
        r"Agent rules",
        r"Service discovery rules",
        r"Other services",
        r"Other integrations",
        r"Event console rules",
        r"Host monitoring rules",
        r"HW/SW Inventory",
        r"SNMP rules",
        r"VM, cloud, container",
    ]

    def __init__(self, page: Page, host: HostDetails, navigate_to_page: bool = True) -> None:
        self.host = host
        self.page_title = f"Effective parameters of {host.name}"
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        """Navigate to 'Effective parameters of <host name>' page.

        This method assumes that the host is already created.
        """
        setup_hosts_page = SetupHost(self.page)
        logger.info("Navigate to '%s' page", self.page_title)
        setup_hosts_page.effective_parameters_button(self.host.name).click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("mode=object_parameters")),
            wait_until="load",
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.section_title(HostEffectiveParameters.sections[0])).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def section_title(self, section_name: str) -> Locator:
        return self.main_area.locator().get_by_role("cell", name=section_name)

    def _section(self, section_name: str) -> Locator:
        return self.main_area.locator(f"table:has(td:text-is('{section_name}'))")

    def _setting_row(self, setting_name: str) -> Locator:
        return self.main_area.locator(f"tr:has(a:text-is('{setting_name}'))")

    @property
    def service_discovery_values(self) -> Locator:
        return self._setting_row("Periodic service discovery").locator("td[class*='settingvalue']")

    @property
    def service_discovery_period(self) -> Locator:
        return self.main_area.locator(
            "td[class='title']:has-text('Perform service discovery every:') + td"
        )

    def expand_section(self, section_name: str) -> None:
        """Expand the section if it is collapsed."""
        section_class = self._section(section_name).get_attribute("class")
        if section_class and "closed" in section_class:
            self.section_title(section_name).click()
            expect(self._section(section_name)).to_have_class(re.compile(r"open"))
