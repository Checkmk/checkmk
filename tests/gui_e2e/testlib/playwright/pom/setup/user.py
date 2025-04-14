#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from abc import abstractmethod
from typing import NamedTuple, override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.users import Users

logger = logging.getLogger(__name__)


class UserData(NamedTuple):
    user_id: str
    full_name: str
    role: str | None = None
    password: str | None = None


class BaseUserPage(CmkPage):
    """Base class for user pages."""

    page_title: str = ""

    @override
    @abstractmethod
    def navigate(self) -> None:
        pass

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.username_text_field).to_be_visible()
        expect(self.full_name_text_field).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def save_button(self) -> Locator:
        return self.main_area.get_suggestion("Save")

    @property
    def username_text_field(self) -> Locator:
        return self.main_area.get_input("user_id")

    @property
    def full_name_text_field(self) -> Locator:
        return self.main_area.get_input("alias")

    @property
    def password_text_field(self) -> Locator:
        return self.main_area.locator("input[name*='_password_']")

    @property
    def _disable_login_checkbox(self) -> Locator:
        return self.main_area.locator().get_by_text("disable the login to this")

    def _role_checkbox(self, role_name: str) -> Locator:
        return (
            self.main_area.locator()
            .get_by_role("cell", name=role_name, exact=True)
            .locator("label")
        )

    def check_role(self, role_name: str, check: bool) -> None:
        if self._role_checkbox(role_name).is_checked() != check:
            self._role_checkbox(role_name).click()

    def check_disable_login(self, check: bool) -> None:
        if self._disable_login_checkbox.is_checked() != check:
            self._disable_login_checkbox.click()


class AddUser(BaseUserPage):
    """Represent the 'Add user' page.

    To navigate: `Setup -> Users -> Add user`.
    """

    page_title = "Add user"

    @override
    def navigate(self) -> None:
        users_page = Users(self.page)
        users_page.add_user_button.click()
        self.page.wait_for_url(url=re.compile(quote_plus("mode=edit_user")), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.username_text_field).to_be_visible()
        expect(self.full_name_text_field).to_be_visible()

    @property
    @override
    def username_text_field(self) -> Locator:
        return self.main_area.get_input("user_id")

    def fill_users_data(self, user_detail: UserData) -> None:
        """Fill user data.

        Notes:
            - this method can be extended to fill more user data
            - role 'Normal monitoring user' is checked by default
        """
        logger.info("Fill users data for user '%s'", user_detail.user_id)
        self.username_text_field.fill(user_detail.user_id)
        self.full_name_text_field.fill(user_detail.full_name)
        if user_detail.role:
            self.check_role(user_detail.role, True)
        if user_detail.password:
            self.password_text_field.fill(user_detail.password)


class EditUser(BaseUserPage):
    """Represent the 'Edit user <username>' page.

    To navigate: `Setup -> Users -> Properties`.
    """

    def __init__(self, page: Page, username: str, navigate_to_page: bool = True) -> None:
        self.username = username
        self.page_title = f"Edit user {username}"
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        users_page = Users(self.page)
        users_page.user_properties_button(self.username).click()
        self.page.wait_for_url(url=re.compile(quote_plus("mode=edit_user")), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.full_name_text_field).to_be_visible()
        expect(self.password_text_field).to_be_visible()
