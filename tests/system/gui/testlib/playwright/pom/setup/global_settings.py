#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from abc import ABC
from typing import override

from playwright.sync_api import expect, Locator, Page

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage
from tests.system.gui.testlib.playwright.pom.setup.distributed_monitoring import (
    DistributedMonitoring,
)

logger = logging.getLogger(__name__)


class GlobalSettings(CmkPage):
    page_title: str = "Global settings"
    dropdown_buttons: list[str] = ["Related", "Display", "Help"]

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Global settings' page")
        self.main_menu.setup_menu(self.page_title).click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Global settings' page")
        _url_pattern = re.escape("wato.py?mode=globalvars")
        self.page.wait_for_url(re.compile(f"{_url_pattern}$"), wait_until="load")
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def _searchbar(self) -> Locator:
        return self.main_area.locator().get_by_role(role="textbox", name="Find on this page ...")

    def setting_link(self, setting_name: str) -> Locator:
        return self.get_link(setting_name)

    def search_settings(self, search_text: str) -> None:
        """Search for a setting using the searchbar."""
        logger.info("Search for setting: %s", search_text)
        self._searchbar.fill(search_text)
        self.main_area.locator().get_by_role(role="button", name="Submit").click()

    def _toggle_button(self, var_name: str) -> Locator:
        self.search_settings(var_name)
        return self.main_area.locator().get_by_role("link", name="Click to toggle this setting")

    def toggle(self, var_name: str) -> None:
        """Toggle a setting on or off."""
        logger.info("Toggle setting: %s", var_name)
        self.main_area.click_and_wait(self._toggle_button(var_name))


class EditGlobalSetting(CmkPage, ABC):
    """General "edit global settings" page"""

    page_title: str = "Edit global setting"
    dropdown_buttons: list[str] = ["Setting", "Display", "Help"]

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def save_button(self) -> Locator:
        return self.main_area.get_suggestion("Save")

    @property
    def factory_settings_button(self) -> Locator:
        # button is named differently depending on current settings
        return self.main_area.get_suggestion("Reset to default").or_(
            self.main_area.get_suggestion("Remove explicit setting")
        )

    @property
    def reset_confirmation_window(self) -> Locator:
        return self.main_area.locator("div[class*='confirm_popup']")

    @property
    def reset_confirmation_button(self) -> Locator:
        return self.reset_confirmation_window.get_by_role("button", name="Reset")

    def to_factory_settings(self, expect_success: bool = True) -> None:
        """Reset the setting to default and confirm the reset.

        Skip when the reset suggestion is disabled: the setting is not
        explicitly configured, so there is nothing to reset.

        Args:
            expect_success: the reset form submit either redirects to the
                'Global settings' page (success) or re-renders this page with
                a validation error (e.g. reset not permitted). Pass True to
                wait for and validate the redirect. Pass False when the reset
                is expected to fail; the caller is then responsible for
                checking the resulting validation error.
        """
        expect(
            self.factory_settings_button,
            message="Neither 'Reset to default' nor 'Remove explicit setting' is visible.",
        ).to_be_visible()
        if "disabled" in (self.factory_settings_button.get_attribute("class") or ""):
            logger.info("The setting is not explicitly configured; nothing to reset")
            return
        self.factory_settings_button.click()
        expect(
            self.reset_confirmation_window, message="The reset confirmation popup did not appear."
        ).to_be_visible()
        self.reset_confirmation_button.click()
        if expect_success:
            GlobalSettings(self.page, navigate_to_page=False)
        else:
            self.page.wait_for_load_state("load")


class EditPiggybackHubGlobally(EditGlobalSetting):
    """Page to edit the global setting 'Enable piggyback-hub'"""

    @override
    def navigate(self) -> None:
        _setting_name = "Enable piggyback-hub"
        logger.info("Navigate to '%s' setting page", _setting_name)
        settings_page = GlobalSettings(self.page)
        settings_page.search_settings(_setting_name)
        settings_page.setting_link(_setting_name).click()
        self.page.wait_for_url(
            url=re.compile(re.escape("varname=site_piggyback_hub")), wait_until="load"
        )

    @property
    def _current_setting_checkbox(self) -> Locator:
        return self.main_area.locator().get_by_role("checkbox")

    def enable_hub(self) -> None:
        if not self._current_setting_checkbox.is_checked():
            self._current_setting_checkbox.click()

    def disable_hub(self) -> None:
        if self._current_setting_checkbox.is_checked():
            self._current_setting_checkbox.click()


class SiteSpecificGlobalSettings(CmkPage):
    """Site-specific global settings page"""

    dropdown_buttons: list[str] = ["Connections", "Display", "Help"]

    def __init__(
        self,
        page: Page,
        site_id: str,
        navigate_to_page: bool = True,
        contain_filter_sidebar: bool = False,
    ):
        self._site_id = site_id
        super().__init__(page, navigate_to_page, contain_filter_sidebar)

    @property
    def page_title(self) -> str:
        return f"Edit site-specific global settings of {self._site_id}"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Edit site-specific global settings of %s' page", self._site_id)

        distributed_monitoring_page = DistributedMonitoring(self.page)
        distributed_monitoring_page.site_specific_global_configuration(self._site_id).click()
        _edit_sites_url_pattern = re.escape(
            f"wato.py?folder=&mode=edit_site_globals&site={self._site_id}"
        )
        self.page.wait_for_url(re.compile(f"{_edit_sites_url_pattern}$"), wait_until="load")

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def _searchbar(self) -> Locator:
        return self.main_area.locator().get_by_role(role="textbox", name="Find on this page ...")

    def setting_link(self, setting_name: str) -> Locator:
        return self.get_link(setting_name)

    def search_settings(self, search_text: str) -> None:
        """Search for a setting using the searchbar."""
        logger.info("Search for setting: %s", search_text)
        self._searchbar.fill(search_text)
        self.main_area.locator().get_by_role(role="button", name="Submit").click()

    def _toggle_button(self, var_name: str) -> Locator:
        self.search_settings(var_name)
        return self.main_area.locator().get_by_role("link", name="Click to toggle this setting")

    def toggle(self, var_name: str) -> None:
        """Toggle a setting on or off."""
        logger.info("Toggle setting: %s", var_name)
        self.main_area.click_and_wait(self._toggle_button(var_name))


class EditSiteSpecificGlobalSetting(CmkPage, ABC):
    """General "edit global settings" page for site-specific settings"""

    dropdown_buttons: list[str] = ["Setting", "Display", "Help"]

    def __init__(
        self,
        page: Page,
        site_id: str,
        navigate_to_page: bool = True,
        contain_filter_sidebar: bool = False,
    ):
        self._site_id = site_id
        super().__init__(page, navigate_to_page, contain_filter_sidebar)

    @property
    def page_title(self) -> str:
        return f"Site-specific global configuration for {self._site_id}"

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def save_button(self) -> Locator:
        return self.main_area.get_suggestion("Save")

    @property
    def factory_settings_button(self) -> Locator:
        # button is named differently depending on current settings
        return self.main_area.get_suggestion("Reset to default").or_(
            self.main_area.get_suggestion("Remove explicit setting")
        )

    @property
    def reset_confirmation_window(self) -> Locator:
        return self.main_area.locator("div[class*='confirm_popup']")

    @property
    def reset_confirmation_button(self) -> Locator:
        return self.reset_confirmation_window.get_by_role("button", name="Reset")

    def to_factory_settings(self, expect_success: bool = True) -> None:
        """Reset the setting to default and confirm the reset.

        Skip when the reset suggestion is disabled: the setting is not
        explicitly configured, so there is nothing to reset.

        Args:
            expect_success: the reset form submit either redirects to the
                'Site-specific global settings' page (success) or re-renders
                this page with a validation error (e.g. reset not permitted).
                Pass True to wait for and validate the redirect. Pass False
                when the reset is expected to fail; the caller is then
                responsible for checking the resulting validation error.
        """
        expect(
            self.factory_settings_button,
            message="Neither 'Reset to default' nor 'Remove explicit setting' is visible.",
        ).to_be_visible()
        if "disabled" in (self.factory_settings_button.get_attribute("class") or ""):
            logger.info("The setting is not explicitly configured; nothing to reset")
            return
        self.factory_settings_button.click()
        expect(
            self.reset_confirmation_window, message="The reset confirmation popup did not appear."
        ).to_be_visible()
        self.reset_confirmation_button.click()
        if expect_success:
            SiteSpecificGlobalSettings(self.page, self._site_id, navigate_to_page=False)
        else:
            self.page.wait_for_load_state("load")


class EditPiggybackHubSiteSpecific(EditSiteSpecificGlobalSetting):
    """Page to edit the site-specific global setting 'Enable piggyback-hub'"""

    def __init__(
        self,
        page: Page,
        site_id: str,
        navigate_to_page: bool = True,
        contain_filter_sidebar: bool = False,
    ):
        self._site_id = site_id
        super().__init__(page, site_id, navigate_to_page, contain_filter_sidebar)

    @override
    def navigate(self) -> None:
        _setting_name = "Enable piggyback-hub"
        logger.info("Navigate to '%s' setting page", _setting_name)
        settings_page = SiteSpecificGlobalSettings(self.page, self._site_id)
        settings_page.search_settings(_setting_name)
        settings_page.setting_link(_setting_name).click()
        self.page.wait_for_url(
            url=re.compile(re.escape("varname=site_piggyback_hub")), wait_until="load"
        )

    @property
    def _current_setting_checkbox(self) -> Locator:
        return self.main_area.locator().get_by_role("checkbox")

    def enable_hub(self) -> None:
        if not self._current_setting_checkbox.is_checked():
            self._current_setting_checkbox.click()

    def disable_hub(self) -> None:
        if self._current_setting_checkbox.is_checked():
            self._current_setting_checkbox.click()
