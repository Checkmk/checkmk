#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator
from playwright.sync_api import TimeoutError as PWTimeoutError

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.testlib.openapi_session import UsersAPI

logger = logging.getLogger(__name__)


class Users(CmkPage):
    """Represent the 'Users' page.

    To navigate: `Setup -> Users`.
    """

    page_title = "Users"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.setup_menu(self.page_title).click()
        _url_pattern: str = quote_plus("wato.py?mode=users")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.add_user_button).to_be_visible()
        expect(self._user_row("cmkadmin")).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def add_user_button(self) -> Locator:
        return self.main_area.get_suggestion("Add user")

    def _user_row(self, username: str) -> Locator:
        return self.main_area.locator(
            f"tr[class*='data']:has(td:nth-child(3):text-is('{username}'))"
        )

    def delete_user_button(self, username: str) -> Locator:
        return self._user_row(username).get_by_role("link", name="Delete")

    def user_properties_button(self, username: str) -> Locator:
        return self._user_row(username).get_by_role("link", name="Properties")

    def _delete_user_confirmation_window(self) -> Locator:
        return self.main_area.locator("div[class*='confirm_popup']:has(h2:has-text('Delete user'))")

    @property
    def delete_user_confirmation_button(self) -> Locator:
        return self._delete_user_confirmation_window().get_by_role("button", name="Delete")

    def delete_user(self, username: str, restapi: UsersAPI | None = None) -> None:
        """Delete a user using the UI.

        Args:
            username (str): Name of the user to be deleted
            restapi (CMKOpenApiSession | None, optional): Fail safe mechanism.
                In case UI elements are not found,
                make sure to delete the user using REST-API. Defaults to None.
        """
        logger.info("Delete user '%s'", username)
        try:
            self.delete_user_button(username).click()
            self.delete_user_confirmation_button.click()
        except PWTimeoutError as _:
            if restapi:
                logger.warning(
                    "fail-safe: could not delete user: '%s' through UI; using REST-API...", username
                )
                restapi.delete(username)
                self.page.reload()
            else:
                raise _
        expect(
            self._user_row(username), message=f"Expected user: '{username}' to be deleted!"
        ).not_to_be_visible()
