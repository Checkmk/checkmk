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
from tests.testlib.openapi_session import UserRoleAPI

logger = logging.getLogger(__name__)


class RolesAndPermissions(CmkPage):
    """Represent the 'Roles & permissions' page.

    To navigate: `Setup -> Roles & permissions`.
    """

    page_title = "Roles & permissions"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.setup_menu(self.page_title).click()
        _url_pattern: str = quote_plus("wato.py?mode=roles")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self._role_row("admin")).to_be_visible()

    @override
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

    def delete_role(self, role_name: str, restapi: UserRoleAPI | None = None) -> None:
        """Delete a user role using the UI.

        Args:
            role_name (str): Name of the role to be deleted.
            restapi (CMKOpenApiSession | None, optional): Fail safe mechanism.
                In case UI elements are not found,
                make sure to delete the role using REST-API. Defaults to None.
        """
        logger.info("Delete role '%s'", role_name)
        try:
            self.delete_role_button(role_name).click()
            self.delete_role_confirmation_button.click()
        except PWTimeoutError as _:
            if restapi:
                logger.warning(
                    "fail-safe: could not delete role: '%s' through UI; using REST-API...",
                    role_name,
                )
                restapi.delete(role_name)
                self.page.reload()
            else:
                raise _
        expect(
            self._role_row(role_name), message=f"Expected role: '{role_name}' to be deleted!"
        ).not_to_be_visible()
