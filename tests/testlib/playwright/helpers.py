#!/usr/bin/env python
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Wrapper for a page, with some often used functionality"""

from abc import ABC, abstractmethod
from typing import List, Union

from playwright.sync_api import expect, Locator, Page
from playwright.sync_api._generated import FrameLocator

from tests.testlib.playwright.e2e_typing import ActivationStates
from tests.testlib.playwright.timeouts import TemporaryTimeout, TIMEOUT_ACTIVATE_CHANGES_MS


class LocatorHelper(ABC):
    """base class for helper classes for certain page elements"""

    def __init__(self, page: Page) -> None:
        self.page = page

    @abstractmethod
    def locator(self, selector: str) -> Locator:
        """return locator for this subpart"""

    def check_success(self, message: str) -> None:
        """check for a success div and its content"""
        expect(self.locator("div.success")).to_have_text(message)

    def check_error(self, message: str) -> None:
        """check for a error div and its content"""
        expect(self.locator("div.error")).to_have_text(message)

    def get_input(self, input_name: str) -> Locator:
        return self.locator(f'input[name="{input_name}"]')

    def get_suggestion(self, suggestion: str) -> Locator:
        return self.locator(f"#suggestions >> text={suggestion}")

    def get_text(self, text: str) -> Locator:
        return self.locator(f"text={text}")

    def get_element_including_texts(self, element_id: str, texts: List[str]) -> Locator:
        has_text_str = "".join([f":has-text('{t}')" for t in texts])
        return self.locator(f"#{element_id}{has_text_str}")

    def get_link_from_title(self, title: str) -> Locator:
        return self.locator(f"a[title='{title}']")

    def get_attribute_label(self, attribute: str) -> Locator:
        return self.locator(f"#attr_{attribute} label")


class MainMenu(LocatorHelper):
    """functionality to find items from the main menu"""

    def locator(self, selector: str) -> Locator:
        return self.page.locator(selector)

    @property
    def user(self) -> Locator:
        """main menu -> User"""
        return self.page.locator("a.popup_trigger:has-text('User')")


class MainFrame(LocatorHelper):
    """functionality to find items from the main menu"""

    def locator(self, selector: str) -> Locator:
        return self.page.frame_locator("iframe[name='main']").locator(selector)

    def check_page_title(self, title: str) -> None:
        """check the page title"""
        expect(self.locator("div.titlebar > a")).to_have_text(title)


class PPage(LocatorHelper):
    """Playwright Page, wrapper around the page"""

    def __init__(self, page: Page, site_id: str) -> None:
        super().__init__(page)
        self.main_menu = MainMenu(self.page)
        self.main_frame = MainFrame(self.page)
        self.site_id = site_id

    def locator(self, selector: str) -> Locator:
        return self.page.locator(selector)

    def login(self, username: str, password: str) -> None:
        """login to cmk"""
        self.page.locator("#input_user").fill(username)
        self.page.locator("#input_pass").fill(password)
        self.page.locator("#_login").click()

    def logout(self) -> None:
        self.main_menu.user.click()
        self.page.locator("text=Logout").click()

    def activate_selected(self) -> None:
        with TemporaryTimeout(self.page, TIMEOUT_ACTIVATE_CHANGES_MS):
            return self.main_frame.locator("#menu_suggestion_activate_selected").click()

    def expect_activation_state(self, activation_state: ActivationStates) -> None:
        self.main_frame.locator(
            f"#site_{self.site_id}_status:has-text('{activation_state}')"
        ).select_text()

    @property
    def megamenu_setup(self) -> Locator:
        return self.main_menu.locator("#popup_trigger_mega_menu_setup")

    def goto_setup_hosts(self) -> None:
        """main menu -> setup -> Hosts"""
        self.megamenu_setup.click()
        return self.main_menu.locator('#setup_topic_hosts a:has-text("Hosts")').click()

    @property
    def megamenu_monitoring(self) -> Locator:
        return self.main_menu.locator("#popup_trigger_mega_menu_monitoring")

    def goto_monitoring_all_hosts(self) -> None:
        """main menu -> monitoring -> All hosts"""
        self.megamenu_monitoring.click()
        return self.main_menu.locator("#monitoring_topic_overview >> text=All hosts").click()

    def select_host(self, host_name: str) -> None:
        self.main_frame.locator(f"td:has-text('{host_name}')").click()
