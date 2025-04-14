#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from typing import Literal, override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class HostSearch(CmkPage):
    """Represents page 'Monitor > Overview > Host search'"""

    page_title: str = "Host search"

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
    ]

    @override
    def navigate(self) -> None:
        logger.info("Navigate to Monitor >> Overview >> %s", self.page_title)
        self.main_menu.monitor_menu("Host search").click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("view_name=searchhost")), wait_until="load"
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is %s page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self._filter_sidebar).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def found_hosts(self) -> Locator:
        return self.main_area.locator("span[class*='host']")

    @property
    def _filter_sidebar(self) -> Locator:
        return self.main_area.locator("div#popup_filters")

    @property
    def _labels_table(self) -> Locator:
        return self._filter_sidebar.locator("tbody[id^='host_labels_1_vs_container']")

    def check_label_filter_applied(
        self,
        logical_operator: Literal["is", "is not", "and", "or", "not"],
        label: str,
        expected_position: int = 0,
    ) -> None:
        """Check that label filter is applied correctly.

        Check that label name and logical operator are correct at the expected position.
        """
        # example of returned result - ['is', 'test_label:foo', 'and', '(Select label)']
        labels_text = self._labels_table.get_by_role("textbox").all_inner_texts()

        assert labels_text[expected_position * 2] == logical_operator, (
            "Logical operator used to filter hosts using labels is incorrect."
        )
        assert labels_text[expected_position * 2 + 1] == label, (
            "Label used to filter hosts is incorrect."
        )
