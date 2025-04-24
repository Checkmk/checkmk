#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from abc import ABC
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.setup.distributed_monitoring import DistributedMonitoring

logger = logging.getLogger(__name__)


class GlobalSettings(CmkPage):
    page_title: str = "Global settings"
    dropdown_buttons: list[str] = ["Related", "Display", "Help"]

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Global settings' page")
        _url_pattern = quote_plus("wato.py?mode=globalvars")
        self.main_menu.setup_menu(self.page_title).click()
        self.page.wait_for_url(re.compile(f"{_url_pattern}$"), wait_until="load")

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Global settings' page")
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
        reset_option_1 = self.main_area.get_suggestion("Reset to default")
        # button is named differently depending on current settings
        if reset_option_1.is_visible():
            return reset_option_1
        return self.main_area.get_suggestion("Remove explicit setting")

    @property
    def reset_confirmation_window(self) -> Locator:
        return self.main_area.locator("div[class*='confirm_popup']")

    @property
    def reset_confirmation_button(self) -> Locator:
        return self.reset_confirmation_window.get_by_role("button", name="Reset")

    def to_factory_settings(self) -> None:
        """Reset and confirm the reset if reset is possible"""
        self.factory_settings_button.click()
        if self.reset_confirmation_window.is_visible():
            self.reset_confirmation_button.click()


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
            url=re.compile(quote_plus("varname=site_piggyback_hub")), wait_until="load"
        )

    @property
    def _current_setting_checkbox(self) -> Locator:
        current_setting_label = "label[for='cb_ve']"
        return self.main_area.locator(current_setting_label)

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
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ):
        self._site_id = site_id
        super().__init__(
            page, navigate_to_page, contain_filter_sidebar, timeout_assertions, timeout_navigation
        )

    @property
    def page_title(self) -> str:
        return f"Edit site specific global settings of {self._site_id}"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Edit site specific global settings of %s' page", self._site_id)

        distributed_monitoring_page = DistributedMonitoring(self.page)
        distributed_monitoring_page.site_specific_global_configuration(self._site_id).click()
        _edit_sites_url_pattern = quote_plus(
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
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ):
        self._site_id = site_id
        super().__init__(
            page, navigate_to_page, contain_filter_sidebar, timeout_assertions, timeout_navigation
        )

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
        reset_option_1 = self.main_area.get_suggestion("Reset to default")
        # button is named differently depending on current settings
        if reset_option_1.is_visible():
            return reset_option_1
        return self.main_area.get_suggestion("Remove explicit setting")

    @property
    def reset_confirmation_window(self) -> Locator:
        return self.main_area.locator("div[class*='confirm_popup']")

    @property
    def reset_confirmation_button(self) -> Locator:
        return self.reset_confirmation_window.get_by_role("button", name="Reset")

    def to_factory_settings(self) -> None:
        """Reset and confirm the reset if reset is possible"""
        self.factory_settings_button.click()
        if self.reset_confirmation_window.is_visible():
            self.reset_confirmation_button.click()


class EditPiggybackHubSiteSpecific(EditSiteSpecificGlobalSetting):
    """Page to edit the site-specific global setting 'Enable piggyback-hub'"""

    def __init__(
        self,
        page: Page,
        site_id: str,
        navigate_to_page: bool = True,
        contain_filter_sidebar: bool = False,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ):
        self._site_id = site_id
        super().__init__(
            page,
            site_id,
            navigate_to_page,
            contain_filter_sidebar,
            timeout_assertions,
            timeout_navigation,
        )

    @override
    def navigate(self) -> None:
        _setting_name = "Enable piggyback-hub"
        logger.info("Navigate to '%s' setting page", _setting_name)
        settings_page = SiteSpecificGlobalSettings(self.page, self._site_id)
        settings_page.search_settings(_setting_name)
        settings_page.setting_link(_setting_name).click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("varname=site_piggyback_hub")), wait_until="load"
        )

    @property
    def _current_setting_checkbox(self) -> Locator:
        current_setting_label = "label[for='cb_ve']"
        return self.main_area.locator(current_setting_label)

    def enable_hub(self) -> None:
        if not self._current_setting_checkbox.is_checked():
            self._current_setting_checkbox.click()

    def disable_hub(self) -> None:
        if self._current_setting_checkbox.is_checked():
            self._current_setting_checkbox.click()
