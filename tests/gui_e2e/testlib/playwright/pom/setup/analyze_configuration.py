#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class AnalyzeConfiguration(CmkPage):
    """Represent the page `Setup -> Maintenance -> Analyze configuration`."""

    def __init__(
        self,
        page: Page,
        navigate_to_page: bool = True,
    ) -> None:
        self.page_title = "Analyze configuration"
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        """Instructions to navigate to `Setup -> Maintenance -> Analyze configuration` page."""
        logger.info(f"Navigate to '{self.page_title}' page")
        self.main_menu.setup_menu(self.page_title).click()
        _url_pattern: str = quote_plus("wato.py?mode=analyze_config")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info(f"Validate that current page is '{self.page_title}' page")
        self.main_area.check_page_title(self.page_title)
        expect(self.analyse_config_table).to_have_count(4)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def analyse_config_table(self) -> Locator:
        return self.main_area.locator("table[class*='analyze_config']")

    @property
    def status_column_values(self) -> Locator:
        return self.main_area.locator("span[class*='state']")

    @property
    def title_column_values(self) -> Locator:
        return self.main_area.locator("td[class*='buttons'] + td")

    def verify_all_expected_checks_are_present(self, expected_checks: list[str]) -> None:
        """Verify that all expected checks are present in the analyze configuration table."""
        titles = self.title_column_values.all_inner_texts()
        assert len(expected_checks) == len(titles), (
            f"Expected {len(expected_checks)} checks, but got {len(titles)} checks."
        )
        for expected_check in expected_checks:
            assert expected_check in titles, (
                f"Expected check '{expected_check}' not found in the analyze configuration table."
            )

    def verify_checks_statuses(self, expected_statues: dict[str, str]) -> None:
        titles = self.title_column_values.all_inner_texts()
        statuses = self.status_column_values.all_inner_texts()
        actual_statuses = dict(zip(titles, statuses))
        assert len(titles) == len(actual_statuses), (
            f"Expected {len(expected_statues)} checks, but got {len(actual_statuses)} checks."
        )
        for title, expected_status in expected_statues.items():
            actual_status = actual_statuses.get(title)
            assert actual_status == expected_status, (
                f"Expected status '{expected_status}' for check '{title}', "
                f"but got '{actual_status}'."
            )
