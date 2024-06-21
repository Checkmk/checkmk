#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

from playwright.sync_api import expect, Locator, Page

from tests.testlib.playwright.pom.page import CmkPage


class ChangePassword(CmkPage):
    """Represent the page `Navigation bar -> User -> User profile -> Change password`."""

    page_title: str = "Change password"

    def __init__(self, page: Page, navigate_to_page: bool = True) -> None:
        super().__init__(page, navigate_to_page)

    def navigate(self) -> None:
        """Navigate to change password page, like a Checkmk GUI user."""
        self.main_menu.user_change_password.click()
        self.page.wait_for_url(url=re.compile("user_change_pw.py$"), wait_until="load")
        self._validate_page()

    def _validate_page(self) -> None:
        self.main_area.check_page_title(self.page_title)
        expect(self.current_password_input).to_be_visible()
        expect(self.new_password_input).to_be_visible()

    @property
    def current_password_input(self) -> Locator:
        return self.main_area.locator("input[name='cur_password']")

    @property
    def new_password_input(self) -> Locator:
        return self.main_area.locator("input[name='password']")

    @property
    def new_password_confirm_input(self) -> Locator:
        return self.main_area.locator("input[name='password2']")

    @property
    def save_button(self) -> Locator:
        return self.main_area.locator("#suggestions >> text=Save")

    def change_password(
        self, current_password: str, new_password: str, confirm_new_password: str | None = None
    ) -> None:
        """Changes the password of the user, but does not check for success or error messages."""
        self.current_password_input.fill(current_password)
        self.new_password_input.fill(new_password)
        if confirm_new_password:
            self.new_password_confirm_input.fill(confirm_new_password)
        self.save_button.click()
