#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Wrapper for a page, with some often used functionality"""

import re
from abc import ABC, abstractmethod
from enum import Enum
from re import Pattern

from playwright.sync_api import expect, Locator, Page

from tests.testlib.playwright.timeouts import TIMEOUT_ASSERTIONS, TIMEOUT_NAVIGATION


class LocatorHelper(ABC):
    """base class for helper classes for certain page elements

    `timeout` defaults to 30 seconds, if not provided.
    """

    def __init__(
        self,
        page: Page,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        # default timeout
        if timeout_assertions is None:
            timeout_assertions = TIMEOUT_ASSERTIONS
        if timeout_navigation is None:
            timeout_navigation = TIMEOUT_NAVIGATION
        # explicitly set all default timeouts
        page.set_default_timeout(timeout_navigation)
        page.set_default_navigation_timeout(timeout_navigation)
        expect.set_options(timeout=timeout_assertions)
        self.page = page

    @abstractmethod
    def locator(self, selector: str) -> Locator:
        """return locator for this subpart"""

    def check_success(self, message: str | Pattern) -> None:
        """check for a success div and its content"""
        expect(self.locator("div.success")).to_have_text(message)

    def check_error(self, message: str | Pattern) -> None:
        """check for an error div and its content"""
        expect(self.locator("div.error")).to_have_text(message)

    def check_warning(self, message: str | Pattern) -> None:
        """check for a warning div and its content"""
        expect(self.locator("div.warning")).to_have_text(message)

    def get_input(self, input_name: str) -> Locator:
        return self.locator(f'input[name="{input_name}"]')

    def get_suggestion(self, suggestion: str) -> Locator:
        return self.locator("#suggestions .suggestion").filter(has_text=re.compile(suggestion))

    def get_text(
        self, text: str, is_visible: bool = True, exact: bool = True, first: bool = True
    ) -> Locator:
        is_visible_str = ">> visible=true" if is_visible else ""
        wrap_text = f"'{text}'" if exact else text
        locator = self.locator(f"text={wrap_text} {is_visible_str}")
        return locator.first if first else locator

    def get_element_including_texts(self, element_id: str, texts: list[str]) -> Locator:
        has_text_str = "".join([f":has-text('{t}')" for t in texts])
        return self.locator(f"#{element_id}{has_text_str}")

    def get_link_from_title(self, title: str) -> Locator:
        return self.locator(f"a[title='{title}']")

    def get_attribute_label(self, attribute: str) -> Locator:
        return self.locator(f"#attr_{attribute} label")


class Keys(Enum):
    """Keys to control the virtual keyboard in playwright."""

    Enter = "Enter"
    Escape = "Escape"
    ArrowUp = "ArrowUp"
    ArrowDown = "ArrowDown"
    ArrowLeft = "ArrowLeft"
    ArrowRight = "ArrowRight"
