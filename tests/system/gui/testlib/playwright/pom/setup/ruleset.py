#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from re import Pattern
from typing import override
from urllib.parse import quote_plus, urljoin

from playwright.sync_api import expect, Locator, Page

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class Ruleset(CmkPage):
    """Represent any page with service ruleset."""

    def __init__(
        self,
        page: Page,
        rule_name: str,
        varname: str,
        navigate_to_page: bool = True,
    ) -> None:
        """
        Args:
            rule_name: Title of the ruleset, as shown in the page heading.
            varname: Internal ruleset name, e.g. "checkgroup_parameters:diskstat".
        """
        self.rule_name = rule_name
        self._escaped_rule_name = re.escape(rule_name).replace("/", r"\/")
        self._varname = varname
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.rule_name)
        # CmkPage.go() is unusable here: self._url is only set after navigate().
        ruleset_url = f"wato.py?mode=edit_ruleset&varname={quote_plus(self._varname)}"
        self.page.goto(urljoin(self.page.url, ruleset_url), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.rule_name)
        self.page.wait_for_url(url=re.compile(re.escape("mode=edit_ruleset")), wait_until="load")
        self.main_area.check_page_title(self.rule_name)
        expect(self.main_area.get_suggestion("Add rule")).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def created_new_rule_message(self) -> Pattern[str]:
        return re.compile(f'Created new rule in rule set "{self._escaped_rule_name}" .*')

    @property
    def add_rule_button(self) -> Locator:
        return self.main_area.get_suggestion("Add rule")

    @property
    def delete_button(self) -> Locator:
        """This button appears in the confirmation popup window after clicking on delete icon."""
        return self.main_area.locator().get_by_role("button", name="Delete")

    def rules_table_header(self, folder_path: str = "Main") -> Locator:
        """Return the header of the 'Rules in folder <folder_path>' table.

        This locator can be used while dragging and dropping the rule to the top.
        Note: folder_path is a full path to the folder, example: "Main / Prod".
        """
        return self.main_area.locator().get_by_role(
            "heading", name=re.compile(f"Rules in folder {folder_path} \\([1-9][0-9]*\\)")
        )

    @property
    def rule_rows(self) -> Locator:
        return self.main_area.locator("tr[class*='data']")

    def _rule_row(self, rule_id: str | int) -> Locator:
        """Return a locator for the specific rule row.

        The rule can be identified by rule position, providing an integer input for this function
        or by rule description, providing a string input for this function.
        """
        match rule_id:
            case str():
                return self.main_area.locator(
                    f"tr:has(td[class*='description']:text-is('{rule_id}'))"
                )
            case int():
                return self.main_area.locator(f"tr:has(td[class*='narrow']:text-is('{rule_id}'))")

    def check_rule_is_present(self, rule_id: str | int) -> None:
        expect(
            self._rule_row(rule_id),
            message=f"Rule '{rule_id}' is not present in the ruleset table",
        ).to_be_visible()

    def rule_position(self, rule_description: str) -> Locator:
        return self._rule_row(rule_description).locator("td[class*='narrow']")

    def rule_source(self, rule_id: str | int) -> Locator:
        return self._rule_row(rule_id).locator("td[class*='source']")

    def rule_values(self, rule_id: str | int) -> Locator:
        return self._rule_row(rule_id).locator("td[class*='value']")

    def move_icon(self, rule_id: str | int) -> Locator:
        return self._rule_row(rule_id).get_by_role("link", name="Move this entry")

    def delete_icon(self, rule_id: str | int) -> Locator:
        return self._rule_row(rule_id).get_by_role("link", name="Delete this rule")

    def delete_rule(self, rule_id: str | int) -> None:
        self.delete_icon(rule_id).click()
        self.delete_button.click()
        self.page.wait_for_load_state("load")
