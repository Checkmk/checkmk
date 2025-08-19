#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import Literal, override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.ruleset import Ruleset

logger = logging.getLogger(__name__)


class AddRuleCPULoad(CmkPage):
    """Represent the 'Add rule: CPU load (not utilization!)' page.

    To navigate: `Setup > Services > Service monitoring rules > CPU load (not utilization!)
    > Add rule: CPU load (not utilization!)`.

    Dependent class for value levels configuration:
        `tests/gui_e2e/testlib/playwright/pom/setup/cpu_load_value_levels.py`.
    """

    rule_name = "CPU load (not utilization!)"
    section_name = "Service monitoring rules"
    url_specific = "%3Acpu_load"
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

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def save_button(self) -> Locator:
        return self.main_area.get_suggestion("Save")

    @property
    def description_text_field(self) -> Locator:
        return self.main_area.get_input("options_p_description")

    def _value_section(self, value_name: str) -> Locator:
        return self.main_area.locator(f"td[class='dictleft']:has(label:text-is('{value_name}'))")

    def levels_checkbox(
        self,
        text: Literal[
            "Levels on CPU load: 1 minute average",
            "Levels on CPU load: 5 minute average",
            "Levels on CPU load: 5 minute average",
        ],
    ) -> Locator:
        section = self._value_section(text)
        return section.locator(f"label[for*='levels1_USE']:text('{text}')")
