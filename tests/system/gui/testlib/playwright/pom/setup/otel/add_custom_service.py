#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage
from tests.system.gui.testlib.playwright.pom.setup.otel.custom_services import CustomServices

logger = logging.getLogger(__name__)


class AddCustomService(CmkPage):
    """Represent the page `Setup -> Telemetry -> Custom Services -> Add custom service`.

    Empty for now (CMK-36035) — only the navigation into the creation flow exists.
    """

    page_title = "Add custom service"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        custom_services_page = CustomServices(self.page)
        self.click_and_wait_for_navigation(
            custom_services_page.add_custom_service_button,
            frame_url=re.compile("mode=create_otel_custom_service"),
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()
