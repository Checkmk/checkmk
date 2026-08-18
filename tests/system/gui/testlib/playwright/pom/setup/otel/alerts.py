#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override

from playwright.sync_api import Locator

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class Alerts(CmkPage):
    """Represent the page `Setup -> Events -> Alerts`."""

    page_title = "Alerts"
    main_menu_name = "Alerts"
    empty_state_text = "No alerts yet"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.click_and_wait_for_navigation(
            self.main_menu.setup_menu(self.main_menu_name, exact=True),
            frame_url=re.compile("mode=otel_alerts"),
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def empty_state(self) -> Locator:
        return self.main_area.locator("div.no-config-bundles")
