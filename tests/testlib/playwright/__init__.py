#!/usr/bin/env python

# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Wrapper for a page, with some often used functionality"""

from abc import ABC

from playwright.sync_api import Page, Locator
from playwright.sync_api._generated import FrameLocator


class LocatorHelper(ABC):
    """base class for helper classes for certain page elements"""
    def __init__(self, page: Page) -> None:
        self.page = page


class MainMenu(LocatorHelper):
    """functionality to find items from the main menu"""

    @property
    def user(self) -> Locator:
        """main menu -> User"""
        return self.page.locator("a.popup_trigger:has-text('User')")


class PPage:
    """Playwright Page, wrapper around the page"""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.main_menu = MainMenu(self.page)

    @property
    def main_frame(self) -> FrameLocator:
        return self.page.frame_locator("iframe[name='main']")

    def login(self, username: str, password: str) -> None:
        """login to cmk"""
        self.page.locator("#input_user").fill(username)
        self.page.locator("#input_pass").fill(password)
        self.page.locator("#_login").click()

    def logout(self) -> None:
        self.main_menu.user.click()
        self.page.locator("text=Logout").click()
