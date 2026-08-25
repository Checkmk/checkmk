#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from typing import override
from urllib.parse import urljoin

from playwright.sync_api import expect, Locator, Page

from tests.system.gui.testlib.host_details import HostDetails
from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class HostStatus(CmkPage):
    """Represents page Monitor > Overview > All hosts > Services of <host name> >
    State of host <host name>.
    """

    dropdown_buttons: list[str] = [
        "Commands",
        "Host",
        "Export",
        "Display",
        "Help",
    ]

    links: list[str] = [
        "Acknowledge problems",
        "Schedule downtime",
        "Filter",
        "Show checkboxes",
        "Services of host",
    ]

    def __init__(
        self,
        page: Page,
        host: HostDetails,
        navigate_to_page: bool = True,
    ) -> None:
        self.host_details = host
        self.page_title = f"State of host {host.name}"
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        """Navigate to 'State of host <host name>' page.
        This method assumes that the host is already created.
        """
        logger.info("Navigate to Monitor >> Overview >> All hosts")
        # The Monitor menu's "All hosts" entry now opens the Vue "All hosts" page instead
        # (see CMK-37778), so this navigates by URL directly to the classic view, which
        # stays reachable even though it is hidden from menu listings.
        # To be adapted when the new "All hosts" page tests are implemented in CMK-38167.
        # `self.go()` isn't available yet: it relies on `self._url`, which
        # `CmkPage.__init__` only sets after `navigate()` returns.
        self.page.goto(urljoin(self.page.url, "view.py?view_name=allhosts"), wait_until="load")

        logger.info("Navigate to 'Services of host %s'", self.host_details.name)
        self.main_area.locator("table.data").get_by_role(
            "link", name=self.host_details.name, exact=True
        ).click()
        services_of_host_url_pattern = (
            re.escape(f"host={self.host_details.name}") + ".*" + re.escape("view_name=host")
        )
        self.page.wait_for_url(url=re.compile(services_of_host_url_pattern), wait_until="load")

        logger.info("Navigate to '%s'", self.page_title)
        self.main_area.click_item_in_dropdown_list(dropdown_button="Host", item="State of host")
        status_of_host_url_pattern = (
            re.escape(f"host={self.host_details.name}") + ".*" + re.escape("view_name=hoststatus")
        )
        self.page.wait_for_url(url=re.compile(status_of_host_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self._table_cell("Host name")).to_be_visible()
        expect(self._table_cell("Host state")).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        mapping = DropdownListNameToID()
        setattr(mapping, "Host", "menu_host_single")
        return mapping

    def _table_cell(self, text: str) -> Locator:
        return self.main_area.locator().get_by_role("cell", name=text, exact=True)

    def host_label(self, label_name: str) -> Locator:
        return self.main_area.locator().get_by_role("link", name=label_name, exact=True)
