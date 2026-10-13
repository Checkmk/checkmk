#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from re import Pattern
from typing import override

from playwright.sync_api import expect, Locator, Page

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage
from tests.system.gui.testlib.playwright.pom.setup.distributed_monitoring import (
    DistributedMonitoring,
)

logger = logging.getLogger(__name__)

RESET_BUTTON_NAME = re.compile(r"^Remove (modification|explicit setting|site-specific value)$")
FAILURE_ALERT_HEADING = re.compile(r"^(Saving|Resetting|Loading) failed$")


class SettingEditor:
    def __init__(self, page: Page, editor_title: str) -> None:
        self.container = page.get_by_role("region", name=editor_title)

    @property
    def save_button(self) -> Locator:
        return self.container.get_by_role("button", name="Save")

    @property
    def error(self) -> Locator:
        return self.container.get_by_role("alert", name=FAILURE_ALERT_HEADING)

    def wait_until_loaded(self) -> None:
        expect(
            self.save_button,
            message="The setting editor did not load: save stays disabled until its value arrives",
        ).to_be_enabled()

    def save(self, expect_success: bool = True) -> None:
        logger.info("Save the setting")
        self.save_button.click()
        self._expect_outcome(expect_success)

    def reset(self, expect_success: bool = True) -> None:
        logger.info("Reset the setting")
        reset_button = self.container.get_by_role("button", name=RESET_BUTTON_NAME)
        expect(
            reset_button,
            message="The setting holds no explicit value in this scope, so it cannot be reset",
        ).to_be_visible()
        reset_button.click()
        self.container.get_by_role("button", name="Remove", exact=True).click()
        self._expect_outcome(expect_success)

    def _expect_outcome(self, expect_success: bool) -> None:
        if expect_success:
            expect(self.container, message="The setting editor did not close").to_be_hidden()
        else:
            expect(self.error, message="The setting editor reports no failure").to_be_visible()


class SettingsOverview(CmkPage):
    page_title: str | Pattern[str]
    editor_title: str

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        expect(self.page, message="Unexpected page title").to_have_title(self.page_title)
        expect(self._searchbox, message="The settings search box is not shown").to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def _wait_for_url(self, url_suffix: str) -> None:
        # A login redirect carries the target page in `_origtarget`; anchor on the path separator.
        self.page.wait_for_url(
            re.compile(r"/" + re.escape(url_suffix) + r"([?&].*)?$"), wait_until="load"
        )

    @property
    def _searchbox(self) -> Locator:
        return self.main_area.locator().get_by_role("searchbox", name="Search settings…")

    def search(self, search_text: str) -> None:
        logger.info("Search for setting: %s", search_text)
        self._searchbox.fill(search_text)

    def switch(self, title: str) -> Locator:
        return self.main_area.locator().get_by_role("switch", name=f"Toggle {title}", exact=True)

    def toggle_error(self, title: str) -> Locator:
        return self.switch(title).locator("xpath=following-sibling::*[@role='alert']")

    def toggle(self, title: str, expect_success: bool = True) -> None:
        logger.info("Toggle setting: %s", title)
        self.search(title)
        switch = self.switch(title)
        toggled_state = "false" if switch.get_attribute("aria-checked") == "true" else "true"
        switch.click()
        if expect_success:
            expect(switch, message=f"The setting '{title}' was not toggled").to_have_attribute(
                "aria-checked", toggled_state
            )
        else:
            expect(
                self.toggle_error(title),
                message=f"Toggling the setting '{title}' was not rejected",
            ).to_be_visible()

    def open_editor(self, title: str) -> SettingEditor:
        logger.info("Open the editor of setting: %s", title)
        self.search(title)
        self.main_area.locator().get_by_role("button", name=f"Edit {title}", exact=True).click()
        editor = SettingEditor(self.page, self.editor_title)
        editor.wait_until_loaded()
        return editor


class GlobalSettings(SettingsOverview):
    page_title: str | Pattern[str] = "Global settings"
    editor_title: str = "Edit global setting"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Global settings' page")
        self.main_menu.setup_menu("Global settings").click()
        self._wait_for_url("global_settings.py")
        self.validate_page()


class SiteSpecificSettings(SettingsOverview):
    page_title: str | Pattern[str] = re.compile("^Site-specific settings of ")
    editor_title: str = "Edit site-specific setting"

    def __init__(self, page: Page, site_id: str, navigate_to_page: bool = True) -> None:
        self._site_id = site_id
        super().__init__(page, navigate_to_page)

    @override
    def navigate(self) -> None:
        logger.info("Navigate to the site-specific settings of site '%s'", self._site_id)
        DistributedMonitoring(self.page).site_specific_settings_link(self._site_id).click()
        self._wait_for_url(f"site_specific_settings.py?site={self._site_id}")
        self.validate_page()
