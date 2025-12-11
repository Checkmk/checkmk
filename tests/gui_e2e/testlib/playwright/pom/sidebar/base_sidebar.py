#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from abc import abstractmethod
from typing import override

from playwright.sync_api import expect, Locator, Page

from tests.gui_e2e.testlib.playwright.helpers import LocatorHelper


class SidebarHelper(LocatorHelper):
    """Base class for sidebar helpers"""

    sidebar_title: str

    def __init__(self, page: Page, validate_sidebar: bool = True) -> None:
        self.page = page
        if validate_sidebar:
            self._validate_sidebar()

    def _validate_sidebar(self) -> None:
        self.expect_to_be_visible()
        self.expect_page_title()
        self.locator().element_handle().wait_for_element_state("stable")

    @property
    def sidebar_title_locator(self) -> Locator:
        """Locator property for the sidebar title."""
        return self.locator().get_by_role("heading", name=self.sidebar_title, exact=True)

    @override
    def locator(
        self,
        selector: str | None = None,
        *,
        has_text: re.Pattern[str] | str | None = None,
        has_not_text: re.Pattern[str] | str | None = None,
        has: Locator | None = None,
        has_not: Locator | None = None,
        check: bool = True,
    ) -> Locator:
        _loc = self._sidebar_locator
        if selector:
            _loc = _loc.locator(selector)
        kwargs = self._build_locator_kwargs(
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )
        _loc = _loc.filter(**kwargs) if kwargs else _loc
        if check:
            self._unique_web_element(_loc)
        return _loc

    @property
    @abstractmethod
    def _sidebar_locator(self) -> Locator:
        """Locator property for the main area of the sidebar.

        It has to be overriden by the children classes.
        """

    def expect_page_title(self) -> None:
        """Verify that the sidebar title is visible."""
        expect(
            self.sidebar_title_locator,
            message=f"'{self.sidebar_title}' sidebar title is not present",
        ).to_be_visible()
