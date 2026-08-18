#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage
from tests.system.gui.testlib.playwright.pom.setup.otel.alerts import Alerts

logger = logging.getLogger(__name__)


class AddAlert(CmkPage):
    """Represent the page `Setup -> Events -> Alerts -> Add alert`.

    Empty for now (CMK-37436) — only the navigation into the creation flow exists.
    """

    page_title = "Add alert"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        alerts_page = Alerts(self.page)
        self.click_and_wait_for_navigation(
            alerts_page.add_alert_button,
            frame_url=re.compile("mode=create_otel_alert"),
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()
