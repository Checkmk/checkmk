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


class SupportDiagnosticsSelectSite(CmkPage):
    """Represent the page 'Support diagnostics' to select site.

    Accessible at `Main menu > Setup > Support diagnostics (1/2)`.
    """

    title = "Support diagnostics"

    @override
    def navigate(self) -> None:
        """Navigate to page."""
        logger.info("Navigate to page '%s'", self.title)
        self.main_menu.setup_menu(self.title).click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        _url_pattern = quote_plus("wato.py?mode=diagnostics")
        self.page.wait_for_url(re.compile(f"{_url_pattern}$"), wait_until="load")
        self.main_area.check_page_title(self.title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def _select_button(self) -> Locator:
        return self.main_area.get_suggestion("Select")

    @property
    def _select_site_combobox(self) -> Locator:
        return self.main_area.locator().get_by_role("combobox", name="site")

    def select_site(self, site_name: str | None = None) -> "SupportDiagnostics":
        if site_name:
            self._select_site_combobox.click()
            self.main_area.locator().get_by_role("option", name=site_name).click()
            expect(
                self._select_site_combobox, message=f"Site '{site_name}' not properly selected"
            ).to_contain_text(site_name)

        self._select_button.click()

        return SupportDiagnostics(self.page, navigate_to_page=False)


class SupportDiagnostics(CmkPage):
    """Represent the page 'Support diagnostics' to select options.

    Accessible at `Main menu > Setup > Support diagnostics (2/2)`.
    """

    title = "Support diagnostics"

    @override
    def navigate(self) -> None:
        """Navigate to page."""
        logger.info("Navigate to page '%s'", self.title)
        SupportDiagnosticsSelectSite(self.page).select_site()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        self.page.wait_for_url(re.compile("wato.py$"), wait_until="load")
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
