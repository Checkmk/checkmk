#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from playwright.sync_api import Locator, Page

from tests.testlib.playwright.pom.page import CmkPage


class ChangePassword(CmkPage):
    """Represent the page `Navigation bar -> User -> User profile -> Change password`."""

    page_title: str = "Change password"

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def navigate(self) -> str:
        """Navigate to change password page, like a Checkmk GUI user."""
        self.click_and_wait(self.main_menu.user_change_password, navigate=True)
        self.main_area.check_page_title(self.page_title)
        self.main_area.page.wait_for_load_state("load")
        return self.page.url

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
