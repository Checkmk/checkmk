#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from typing import NamedTuple, override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.roles_and_permissions import RolesAndPermissions

logger = logging.getLogger(__name__)


class RoleData(NamedTuple):
    role_id: str
    alias: str
    copy_from_role_id: str


class EditRole(CmkPage):
    """Represent the 'Edit role <role name>' page.

    To navigate: `Setup -> Roles & permissions -> Edit role <role name>`.
    """

    def __init__(self, page: Page, role_name: str, navigate_to_page: bool = True) -> None:
        self.role_name = role_name
        self.page_title = f"Edit role {role_name}"
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        roles_and_permissions_page = RolesAndPermissions(self.page)
        roles_and_permissions_page.role_properties_button(self.role_name).click()
        self.page.wait_for_url(url=re.compile(quote_plus("mode=edit_role")), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.internal_id_text_field).to_be_visible()
        expect(self.alias_text_field).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def save_button(self) -> Locator:
        return self.main_area.get_suggestion("Save")

    @property
    def internal_id_text_field(self) -> Locator:
        return self.main_area.get_input("id")

    @property
    def alias_text_field(self) -> Locator:
        return self.main_area.get_input("alias")
