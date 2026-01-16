#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.ruleset import Ruleset

logger = logging.getLogger(__name__)


class AddRuleFilesystems(CmkPage):
    """Represent the 'Add rule: File systems (used space and growth)' page.

    To navigate: `Setup > Services > Service monitoring rules > File systems (used space and growth)
    > Add rule: File systems (used space and growth)`.
    """

    rule_name = "File systems (used space and growth)"
    section_name = "Service monitoring rules"
    url_specific = "%3Afilesystem"
    url_pattern = "varname=checkgroup_parameters%s&mode=new_rule"

    @override
    def navigate(self) -> None:
        service_rules_page = Ruleset(self.page, self.rule_name, self.section_name)
        logger.info("Navigate to 'Add rule: %s' page", self.rule_name)
        service_rules_page.add_rule_button.click()
        self.page.wait_for_url(
            url=re.compile(quote_plus(self.url_pattern % self.url_specific)),
            wait_until="load",
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Add rule: %s' page", self.rule_name)
        self.main_area.check_page_title(f"Add rule: {self.rule_name}")
        expect(self.description_text_field).to_be_visible()
        expect(self._levels_for_used_free_space_checkbox).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def save_button(self) -> Locator:
        return self.main_area.get_suggestion("Save")

    @property
    def description_text_field(self) -> Locator:
        return self.main_area.locator().get_by_role("textbox", name="Description")

    def _value_section(self, value_name: str) -> Locator:
        return self.main_area.locator(f"td[class='dictleft']:has(label:text-is('{value_name}'))")

    @property
    def _levels_for_used_free_space_checkbox(self) -> Locator:
        return self._value_section("Levels for used/free space").locator("label")

    @property
    def levels_for_used_free_space_warning_text_field(self) -> Locator:
        return self._value_section("Levels for used/free space").locator(
            "input[name*='_p_levels_0_0_0']"
        )

    @property
    def explicit_hosts_checkbox(self) -> Locator:
        return self.main_area.locator().get_by_role("checkbox", name="Explicit hosts")

    @property
    def explicit_hosts_combobox(self) -> Locator:
        return (
            self.main_area.locator()
            .get_by_role("group", name="Explicit hosts")
            .get_by_role("combobox")
            .first
        )

    @property
    def explicit_hosts_listbox(self) -> Locator:
        return (
            self.main_area.locator()
            .get_by_role("group", name="Explicit hosts")
            .get_by_role("listbox")
        )

    def check_levels_for_user_free_space(self, check: bool) -> None:
        if self._levels_for_used_free_space_checkbox.is_checked() != check:
            self._levels_for_used_free_space_checkbox.click()

    def select_explicit_host(self, host_name: str) -> None:
        self.explicit_hosts_checkbox.check()
        expect(
            self.explicit_hosts_combobox,
            message=(
                "'Explicit hosts' combobox not present after checking 'Explicit hosts' checkbox"
            ),
        ).to_be_visible()

        self.explicit_hosts_combobox.click()
        expect(
            self.explicit_hosts_listbox,
            message="'Explicit hosts' listbox not deployed",
        ).to_be_visible()

        self.explicit_hosts_listbox.get_by_role("option", name=host_name).click()
        expect(
            self.explicit_hosts_combobox,
            message=f"Host '{host_name}' not selected",
        ).to_have_text(host_name)
