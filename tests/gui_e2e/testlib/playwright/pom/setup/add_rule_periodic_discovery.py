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


class AddRulePeriodicServiceDiscovery(CmkPage):
    """Represent the 'Add rule: Periodic service discovery' page.

    To navigate: `Setup -> Service discovery rules -> Periodic service discovery -> Add rule`.
    """

    rule_name = "Periodic service discovery"

    @override
    def navigate(self) -> None:
        service_rules_page = Ruleset(self.page, self.rule_name)
        logger.info("Navigate to 'Add rule: %s' page", self.rule_name)
        service_rules_page.add_rule_button.click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("varname=periodic_discovery&mode=new_rule")),
            wait_until="load",
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Add rule: %s' page", self.rule_name)
        self.main_area.check_page_title(f"Add rule: {self.rule_name}")
        expect(self.description_text_field).to_be_visible()
        expect(self.hours_text_field).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def description_text_field(self) -> Locator:
        return self.main_area.get_input("options_p_description")

    @property
    def hours_text_field(self) -> Locator:
        return self.main_area.locator("div.vs_age input").nth(1)

    @property
    def save_button(self) -> Locator:
        return self.main_area.get_suggestion("Save")
