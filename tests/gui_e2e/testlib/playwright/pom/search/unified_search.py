#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
from re import Pattern
from typing import override

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import LocatorHelper
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.gui_e2e.testlib.playwright.pom.search.parts.provider_select import ProviderSelect
from tests.gui_e2e.testlib.playwright.pom.search.parts.recently_results import RecentlyResults
from tests.gui_e2e.testlib.playwright.pom.search.parts.search_operator_select import (
    SearchOperatorSelect,
)
from tests.gui_e2e.testlib.playwright.pom.search.parts.search_results import SearchResults

logger = logging.getLogger(__name__)


class UnifiedSearchSlideout(LocatorHelper):
    """Represents main menu 'Search' slideout"""

    def __init__(self, cmk_page: CmkPage) -> None:
        self.cmk_page = cmk_page
        logger.info("Navigate to 'Main menu' -> 'Search' slideout")
        if not self.slideout.is_visible():
            self.cmk_page.main_menu.search_menu().click()
        logger.info("Validate that the unified search is open")
        self.validate()

    @override
    def locator(
        self,
        selector: str | None = None,
        *,
        has_text: Pattern[str] | str | None = None,
        has_not_text: Pattern[str] | str | None = None,
        has: Locator | None = None,
        has_not: Locator | None = None,
    ) -> Locator:
        if not selector:
            selector = "xpath=."
        _loc = self.cmk_page.locator("#check_mk_sidebar").locator(selector)
        kwargs = self._build_locator_kwargs(
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )
        _loc = _loc.filter(**kwargs) if kwargs else _loc
        return _loc

    def validate(self) -> None:
        """Validate that the unified search slideout is open"""
        logger.info("Validate that the unified search slideout is open")
        expect(self.slideout).to_be_visible()
        logger.info("Validate that the provider select is visible")
        expect(self.provider_select.locator).to_be_visible()
        logger.info("Validate that the search operator select is visible")
        expect(self.search_operator_select.locator).to_be_visible()
        logger.info("Validate that the focus is on the input field")
        expect(self.input).to_be_focused()

    @property
    def slideout(self) -> Locator:
        return self.cmk_page.locator(".main-menu-popup-menu.unified-search-app")

    @property
    def input(self) -> Locator:
        return self.slideout.get_by_placeholder("Search")

    @property
    def provider_select(self) -> ProviderSelect:
        return ProviderSelect(locator=self.slideout.locator(".unified-search-provider-switch"))

    @property
    def search_operator_select(self) -> SearchOperatorSelect:
        return SearchOperatorSelect(
            locator=self.slideout.locator(".unified-search-operator-switch")
        )

    @property
    def slash_search_operators(self) -> SearchOperatorSelect:
        self.input.type("/")
        return SearchOperatorSelect(
            locator=self.slideout.locator(".unified-search-filters__suggestions")
        )

    @property
    def recently_viewed(self) -> RecentlyResults:
        return RecentlyResults(self.slideout.locator(".recently-viewed"))

    @property
    def recently_searched(self) -> RecentlyResults:
        return RecentlyResults(self.slideout.locator(".recently-searched"))

    @property
    def search_results(self) -> SearchResults:
        return SearchResults(self.slideout.locator(".cmk-unified-search-result-tabs"))

    def exec_service_host_search(self, search_term: str) -> None:
        self.input.fill(search_term)
        self.input.press("Enter")

    def exec_search(self, search_term: str) -> SearchResults:
        self.input.fill(search_term)
        return self.search_results
