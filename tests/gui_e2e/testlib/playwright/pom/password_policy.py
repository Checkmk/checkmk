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
from tests.gui_e2e.testlib.playwright.pom.setup.global_settings import GlobalSettings

logger = logging.getLogger(__name__)


class PasswordPolicy(CmkPage):
    """Represents the Password Policy page in the GUI.

    This page is accessible via the navigation path:
    Navigation bar -> Setup -> Global settings -> User management -> Password policy.
    """

    page_title: str = "Change password"

    @property
    def _num_groups_label(self) -> Locator:
        """Returns the label for the number of character groups checkbox."""
        return self.main_area.locator("label[for='cb_ve_p_num_groups_USE']")

    @property
    def _num_groups_checkbox(self) -> Locator:
        """Returns the checkbox for the number of character groups."""
        return self.main_area.locator("input#cb_ve_p_num_groups_USE")

    @override
    def navigate(self) -> None:
        _setting_name = "Password policy for local accounts"
        logger.info("Navigate to '%s' setting page", _setting_name)
        settings_page = GlobalSettings(self.page)
        settings_page.search_settings(_setting_name)
        settings_page.setting_link(_setting_name).click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("varname=password_policy")), wait_until="load"
        )

    @override
    def validate_page(self) -> None:
        expect(
            self._num_groups_label,
            message="'Number of character groups to use' label is not visible",
        ).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def _save_options(self) -> None:
        """Saves the options on the page."""
        self.main_area.get_suggestion("Save").click()

    def _set_state_of_number_of_character_groups_checkbox(self, *, check_state: bool) -> None:
        """Sets the check state of the number of character groups checkbox.

        Args:
            check_state: The desired check state (True for checked, False for unchecked).
        """
        if self._num_groups_checkbox.is_checked() != check_state:
            self._num_groups_label.click()

    def set_the_number_of_character_groups(self, number_of_groups: str) -> None:
        """Sets the number of character groups for the password policy.

        Args:
            number_of_groups: The number of character groups to set.
        """
        logger.info("Set the number of character groups to %s", number_of_groups)

        self._set_state_of_number_of_character_groups_checkbox(check_state=True)

        self.main_area.locator("input[name='ve_p_num_groups']").fill(number_of_groups)
        self._save_options()

    def disable_the_number_of_charachter_groups(self) -> None:
        """Disables the number of character groups for the password policy."""
        logger.info("Disable the number of character groups")

        self._set_state_of_number_of_character_groups_checkbox(check_state=False)
        self._save_options()
