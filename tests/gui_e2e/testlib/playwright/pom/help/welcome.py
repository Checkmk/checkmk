#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from typing import override

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class WelcomePage(CmkPage):
    """Represents the Welcome page of Checkmk."""

    page_title: str = "Welcome to Checkmk"

    @override
    def navigate(self) -> None:
        """Navigate to the Welcome page."""
        self.navigate_via_help_menu()

    def navigate_via_help_menu(self) -> None:
        """Navigate to Welcome page using the Help menu."""
        logger.info("Navigate to 'Welcome' page via Help menu")
        self.main_menu.help_menu("Welcome page").click()
        self.validate_page()

    def navigate_via_home_button(self) -> None:
        """Navigate to the Welcome page."""
        logger.info("Navigate to 'Welcome' page via home button")
        self.main_menu.main_page.click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        """Validate that the Welcome page is displayed."""
        logger.info("Validate that current page is 'Welcome' page")
        self.page.wait_for_url(re.compile(r"welcome\.py"), wait_until="load")
        expect(
            self.welcome_app,
            message="WelcomeApp component is not visible",
        ).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def welcome_app(self) -> Locator:
        """Locator for the main WelcomeApp component."""
        return self.main_area.locator("cmk-welcome")

    @property
    def welcome_footer(self) -> Locator:
        """Locator for the WelcomeApp footer section."""
        return self.welcome_app.locator(".welcome-footer")

    @property
    def show_on_start_checkbox(self) -> Locator:
        """Locator for the 'Show welcome page on start' checkbox."""
        return self.welcome_footer.get_by_role("checkbox", name="Show welcome page on start")

    def disable_show_on_start(self) -> None:
        """Disable the 'Show welcome page on start' option."""
        logger.info("Disable 'Show welcome page on start'")
        expect(
            self.show_on_start_checkbox,
            message="'Show welcome page on start' checkbox is not visible",
        ).to_be_visible()
        self.show_on_start_checkbox.uncheck()
        logger.info("'Show welcome page on start' disabled")
        expect(
            self.show_on_start_checkbox,
            message="'Show welcome page on start' checkbox should not be checked",
        ).not_to_be_checked()

    def enable_show_on_start(self) -> None:
        """Enable the 'Show welcome page on start' option."""
        logger.info("Enable 'Show welcome page on start'")
        expect(
            self.show_on_start_checkbox,
            message="'Show welcome page on start' checkbox is not visible",
        ).to_be_visible()
        self.show_on_start_checkbox.check()
        logger.info("'Show welcome page on start' enabled")
        expect(
            self.show_on_start_checkbox,
            message="'Show welcome page on start' checkbox should be checked",
        ).to_be_checked()
