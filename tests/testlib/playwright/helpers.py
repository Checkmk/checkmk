#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Wrapper for a page, with some often used functionality"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pprint import pformat
from re import Pattern
from typing import NamedTuple

from playwright.sync_api import Error, expect, Frame, Locator, Page
from playwright.sync_api import TimeoutError as PWTimeoutError

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
        expect(self.locator("div.error"), "Invalid text in the error message box.").to_have_text(
            message
        )

    def get_error_text(self) -> str | None:
        """get error text content"""
        return self.locator("div.error").text_content()

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

    def click_and_wait(
        self,
        locator: Frame | Locator | Page,
        navigate: bool = False,
        expected_locator: Locator | None = None,
        reload_on_error: bool = False,
        max_tries: int = 10,
        **click_kwargs: dict[str, bool | float | int | str] | None,
    ) -> None:
        """Wait until the specified locator could be clicked.

        After a successful click, wait until the current URL has changed and is loaded
        or an expected locator is found.
        """
        latest_excp: Exception
        _page = locator if isinstance(locator, Page) else locator.page
        url = _page.url
        clicked = False

        for _ in range(max_tries):
            if not clicked:
                try:
                    locator.click(**click_kwargs)  # type: ignore[arg-type]
                    clicked = True
                except PWTimeoutError as excp:
                    latest_excp = excp

            if clicked:
                _page.wait_for_load_state(state="load")
                try:
                    if navigate:
                        expect(_page).not_to_have_url(url)
                    if expected_locator:
                        expect(expected_locator).to_be_visible()
                    return
                except AssertionError as excp:
                    latest_excp = excp

            try:
                if reload_on_error:
                    self.page.reload(wait_until="load")
            except Error as excp:
                latest_excp = excp
                continue

        raise AssertionError(
            "Current URL did not change; expected locator not found or page failed to reload."
            f"Latest exception:\n{pformat(latest_excp)}\n"
        )

    def _unique_web_element(self, web_element: Locator) -> None:
        """Validate the web selector under consideration is unique."""
        expect(web_element).to_be_visible()
        expect(web_element).to_have_count(1)


class Keys(Enum):
    """Keys to control the virtual keyboard in playwright."""

    Enter = "Enter"
    Escape = "Escape"
    ArrowUp = "ArrowUp"
    ArrowDown = "ArrowDown"
    ArrowLeft = "ArrowLeft"
    ArrowRight = "ArrowRight"


class CmkCredentials(NamedTuple):
    """Credentials to a Checkmk site."""

    username: str
    password: str


@dataclass
class DropdownListNameToID:
    """Common Checkmk UI mapping between `dropdown list`s and `menu ID`s."""

    Commands: str = "menu_commands"
    Display: str = "menu_display"
    Export: str = "menu_export"
    Help: str = "menu_help"
    Related: str = "menu_related"
