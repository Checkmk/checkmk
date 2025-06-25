#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class AgentBakeryPage(CmkPage):
    page_title = "Windows, Linux, Solaris, AIX"

    @property
    def bake_and_sign_agents_button(self) -> Locator:
        return self.main_area.get_suggestion("Bake and sign agents")

    @property
    def key_to_sign_with_dropdown_list(self) -> Locator:
        return self.main_area.locator("#select2-key_p_key-container")

    @property
    def key_passphrase_dropdown_list(self) -> Locator:
        return self.main_area.locator(
            "#select2-key_p_key-results > li.select2-results__option[role='option']"
        )

    @property
    def sign_agents_button(self) -> Locator:
        return self.main_area.get_suggestion("Sign agents")

    @property
    def bake_and_sign_button(self) -> Locator:
        return self.main_area.get_input("create")

    @property
    def baking_success_msg(self) -> Locator:
        return self.main_area.get_text("Agent baking successful")

    @property
    def key_passphrase_input(self) -> Locator:
        return self.main_area.get_input("key_p_passphrase")

    @override
    def navigate(self) -> None:
        """Go to `Setup > Windows, Linux, Solaris, AIX` / Agent bakery page."""
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.setup_menu(self.page_title).click()
        self.page.wait_for_url(re.compile(quote_plus("wato.py?mode=agents")), wait_until="load")
        self.bake_and_sign_agents_button.click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def bake_and_sign(self, key_name: str, passphrase: str) -> None:
        self.key_to_sign_with_dropdown_list.click()
        self.key_passphrase_dropdown_list.filter(has_text=key_name).first.click()
        self.main_area.get_text(key_name).click()
        self.key_passphrase_input.fill(passphrase)

    def assert_baking_succeeded(self) -> None:
        expect(
            self.baking_success_msg,
            "Message box with text 'Agent baking successful' was not found.",
        ).to_be_visible()

    def check_sign_buttons_disabled(self) -> None:
        expect(
            self.bake_and_sign_agents_button,
            "The 'Bake and sign agents' button should be disabled after key deletion, but isn't.",
        ).to_have_class(re.compile("disabled"))
        expect(
            self.sign_agents_button,
            "The 'Sign agents' button should be disabled after key deletion, but isn't.",
        ).to_have_class(re.compile("disabled"))
