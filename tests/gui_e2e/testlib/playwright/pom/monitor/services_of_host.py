#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.monitor.all_hosts import AllHosts
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.services_table import ServicesTable

logger = logging.getLogger(__name__)


class ServicesOfHostPage(CmkPage):
    """Represent 'Services of host' page.

    To navigate: 'Monitor > Overview > (All hosts > Host) > Services of host'.
    """

    def __init__(
        self,
        page: Page,
        host_name: str,
        navigate_to_page: bool = True,
    ) -> None:
        self.host_name = host_name
        self.page_title = f"Services of host {host_name}"
        super().__init__(page=page, navigate_to_page=navigate_to_page)
        self.services_table = ServicesTable(self.main_area)

    @override
    def navigate(self) -> None:
        all_hosts_page = AllHosts(self.page)
        all_hosts_page.get_host_link(self.host_name).click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is %s page", self.page_title)
        self.page.wait_for_url(url=re.compile(quote_plus("view_name=host")), wait_until="load")
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()
