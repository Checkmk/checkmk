#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class MKPManagerPage(CmkPage):
    """Represent the page `setup -> Maintenance -> Extension packages`."""

    page_title = "Extension packages"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.setup_menu(self.page_title).click()
        self.page.wait_for_url(re.compile(quote_plus("wato.py?mode=mkps")), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def enable_buttons(self) -> Locator:
        """All `Enable this package` icon buttons on the page."""
        return self.main_area.locator().get_by_role("link", name="Enable this package")
