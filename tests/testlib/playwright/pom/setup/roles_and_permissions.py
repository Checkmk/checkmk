#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.testlib.playwright.helpers import DropdownListNameToID
from tests.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class RolesAndPermissions(CmkPage):
    """Represent the 'Roles & permissions' page.

    To navigate: `Setup -> Roles & permissions`.
    """

    page_title = "Roles & permissions"

    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.setup_menu(self.page_title).click()
        _url_pattern: str = quote_plus("wato.py?mode=roles")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self._validate_page()

    def _validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self._role_row("admin")).to_be_visible()

    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def _role_row(self, role_name: str) -> Locator:
        return self.main_area.locator(
            f"tr[class*='data']:has(td:nth-child(3):text-is('{role_name}'))"
        )

    def _role_button(self, role_name: str, button_name: str) -> Locator:
        return self._role_row(role_name).get_by_role("link", name=button_name)

    def clone_role_button(self, role_name: str) -> Locator:
        return self._role_button(role_name, "Clone")

    def role_properties_button(self, role_name: str) -> Locator:
        return self._role_button(role_name, "Properties")

    def delete_role_button(self, role_name: str) -> Locator:
        return self._role_button(role_name, "Delete this role")

    def _delete_role_confirmation_window(self) -> Locator:
        return self.main_area.locator("div[class*='confirm_popup']:has(h2:has-text('Delete role'))")

    @property
    def delete_role_confirmation_button(self) -> Locator:
        return self._delete_role_confirmation_window().get_by_role("button", name="Delete")

    def delete_role(self, role_name: str) -> None:
        logger.info("Delete role '%s'", role_name)
        self.delete_role_button(role_name).click()
        self.delete_role_confirmation_button.click()
        expect(self._role_row(role_name)).not_to_be_visible()
