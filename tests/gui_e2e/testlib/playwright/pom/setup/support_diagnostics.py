#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Consolidate objects and functions specific to the page 'Support diagnostics'.


'Support diagnostics' are accessible using 'Setup'.
"""

import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.background_jobs import BackgroundJobDetails

logger = logging.getLogger(__name__)


class SupportDiagnostics(CmkPage):
    """Represent the page 'Support diagnostics'.

    Accessible at `Main menu > Setup > Support diagnostics`.
    """

    title = "Support diagnostics"

    @override
    def navigate(self) -> None:
        """Navigate to page."""
        logger.info("Navigate to page '%s'", self.title)
        _url_pattern = quote_plus("wato.py?mode=diagnostics")
        self.main_menu.setup_menu(self.title).click()
        self.page.wait_for_url(re.compile(f"{_url_pattern}$"), wait_until="load")

    @override
    def validate_page(self) -> None:
        expect(
            self.collect_diagnostics_button,
            message="Expected 'Collect diagnostics' button to be enabled!",
        ).to_be_enabled()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def collect_diagnostics_button(self) -> Locator:
        return self.main_area.get_suggestion("Collect diagnostics")

    def job_details(self) -> BackgroundJobDetails:
        """Navigate to diagnostic job details."""
        logger.info("Navigate to 'Diagnostic job details'.")
        self.collect_diagnostics_button.click()
        return BackgroundJobDetails(self.page, navigate_to_page=False)
