#!/usr/bin/env python

# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Wrapper for a page, with some often used functionality"""

from abc import ABC, abstractmethod

from playwright.sync_api import expect, Locator, Page
from playwright.sync_api._generated import FrameLocator


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

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.main_menu = MainMenu(self.page)
        self.main_frame = MainFrame(self.page)

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
