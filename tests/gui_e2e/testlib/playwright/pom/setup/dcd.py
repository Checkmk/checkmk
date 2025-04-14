#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class DCD(CmkPage):
    """Represent the page 'Dynamic host management', which configures the DCD.

    Accessible at,
    Setup > Hosts > Dynamic host management
    """

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Dynamic host management' page")
        self.main_menu.setup_menu("Dynamic host management").click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("mode=dcd_connections")), wait_until="load"
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Dynamic host management' page")
        self.main_area.check_page_title("Dynamic host management")
        expect(self.add_connection_button).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def add_connection_button(self) -> Locator:
        return self.main_area.locator().get_by_role("link", name="Add connection")

    def connection_row(self, identifier: str, exact: bool = False) -> Locator:
        """Return a locator for a connection.

        The identifier should be a uniquely identifying string within a cell of the row, like the
        connection name/ID. Use `exact=True` to match the entire cell contents.
        """
        return self.main_area.locator().locator(
            "tr.data",
            has=self.main_area.locator().get_by_role("cell", name=identifier, exact=exact),
        )
