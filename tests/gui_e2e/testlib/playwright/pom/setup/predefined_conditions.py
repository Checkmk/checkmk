#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from typing import Literal, override
from urllib.parse import quote_plus

from playwright.sync_api import Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class AddPredefinedCondition(CmkPage):
    """Represents page `Setup -> General -> Predefined conditions -> Add predefined condition`."""

    page_title: str = "Add predefined condition"

    @override
    def navigate(self) -> None:
        """Instructions to navigate to `Setup -> General -> Predefined conditions -> Add predefined
        condition`."""
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.setup_menu("Predefined conditions", show_more=True).click()
        self.get_link(self.page_title).click()
        _url_pattern: str = quote_plus("wato.py?mode=edit_predefined_condition")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)

    @property
    def add_condition_to_host_label_button(self) -> Locator:
        return self._host_labels_row.get_by_role("link", name="Add to condition")

    @property
    def _host_labels_row(self) -> Locator:
        return self.main_area.locator("tr").filter(
            has=self.main_area.locator().get_by_role("cell", name="Host labels")
        )

    @property
    def save_predefined_condition_button(self) -> Locator:
        return self.main_area.locator("div.suggestion").filter(has_text="Save")

    def _check_natural_number(self, number: int) -> None:
        if number <= 0:
            raise ValueError("Expected to be a natural number; positive, non-zero)!")

    def _host_label_group_row(self, group_number: int) -> Locator:
        """Returns the desired row corresponding to a 'label group'."""
        self._check_natural_number(group_number)
        return (
            self._host_labels_row.locator("tbody[id*='host_label_groups_container']").locator(
                "tr[id*='host_label_groups_entry']"
            )
        ).nth(group_number - 1)

    def host_label_row(self, group_number: int = 1, row_number: int = 1) -> Locator:
        """Returns web-element correspodning to a 'label row' within a 'label group'.

        By default, returns the first 'label row' in the first 'label group'.
        `group number` and `row number` should be natural numbers; positive and non-zero.
        """

        self._check_natural_number(row_number)
        label_rows = (
            self._host_label_group_row(group_number)
            .locator("tbody[id*='container']")
            .locator("tr[id*='entry']")
        )
        return label_rows.nth(row_number - 1)

    def add_host_label(
        self,
        condition: Literal["is", "is not", "and", "or", "not"],
        label_text: str,
        group_number: int = 1,
        row_number: int = 1,
    ) -> None:
        """Add a host label to the page with the provided condition.

        By default, first 'label row' present within the first 'label group' is updated.
        `group number` and `row number` should be natural numbers; positive and non-zero.
        """
        main_area = self.main_area.locator()

        # condition
        (self.host_label_row(group_number, row_number).get_by_role("textbox").nth(0)).click()
        main_area.get_by_role("option", name=condition, exact=True).click()

        # label field
        (self.host_label_row(group_number, row_number).get_by_role("textbox").nth(1)).click()
        main_area.get_by_role("searchbox").fill(label_text)
        main_area.get_by_role("option", name=label_text).click()
