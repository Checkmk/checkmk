#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from typing import override

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class ElementTopList(CmkPage):
    """Base class for 'Edit element: Top list' and 'Add element: Top list' pages."""

    page_title = ""

    @override
    def navigate(self) -> None:
        raise NotImplementedError(
            f"Navigate method for '{self.page_title}' is not implemented. The navigation to "
            "this page can vary based on the dashboard and the specific element to be edited. ",
        )

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self._section("Context / Search Filters")).to_be_visible()
        expect(self._section("Properties")).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def save_button(self) -> Locator:
        return self.main_area.get_suggestion("Save")

    def _section(self, section_name: str) -> Locator:
        return self.main_area.locator(f"table:has(td:text-is('{section_name}'))")

    def host_filter(self, filter_name: str) -> Locator:
        return self.main_area.locator(
            f"table#context_host_table >> tr:has(span:text-is('{filter_name}'))"
        )

    def service_filter(self, filter_name: str) -> Locator:
        return self.main_area.locator(
            f"table#context_service_table >> tr:has(span:text-is('{filter_name}'))"
        )

    @property
    def host_filter_field(self) -> Locator:
        return self.main_area.locator("span[aria-labelledby*='host_choice']")

    @property
    def searchbox(self) -> Locator:
        return self.main_area.locator().get_by_role("searchbox")

    def search_option(self, option_name: str) -> Locator:
        return self.main_area.locator().get_by_role("option", name=option_name, exact=True)

    @property
    def host_filter_add_filter_button(self) -> Locator:
        return self.main_area.locator("#context_host_add")

    @property
    def select_item_field(self) -> Locator:
        return self.main_area.locator().get_by_text("(Select item)")

    @property
    def select_label_field(self) -> Locator:
        return self.main_area.locator().get_by_text("(Select label)")

    @property
    def select_metric_field(self) -> Locator:
        return self.main_area.locator().get_by_text("(Select metric)")

    @property
    def _show_service_name_checkbox(self) -> Locator:
        return self.main_area.locator().get_by_text("Show service name")

    @property
    def service_exact_match_search_field(self) -> Locator:
        return self.service_filter("Service (exact match)").get_by_role("textbox")

    @property
    def metric_search_field(self) -> Locator:
        return self.main_area.locator("span#select2-type_p_metric-container")

    def remove_host_filter_button(self, filter_name: str) -> Locator:
        return self.host_filter(filter_name).get_by_role("link", name="Remove filter")

    def _select_host_filter(self, filter_name: str) -> None:
        self.host_filter_field.click()
        self.searchbox.fill(filter_name)
        self.search_option(filter_name).click()

    def _apply_host_filter(self, filter_value: str) -> None:
        self.host_filter_add_filter_button.click()
        self.select_item_field.click()
        self.search_option(filter_value).click()

    def add_host_filter_site(self, site_name: str) -> None:
        self._select_host_filter("Site")
        self._apply_host_filter(site_name)

    def add_host_filter_host_labels(self, label: str) -> None:
        self._select_host_filter("Host labels")
        self.host_filter_add_filter_button.click()
        self.select_label_field.click()
        self.search_option(label).click()

    def select_metric(self, metric: str) -> None:
        self.select_metric_field.click()
        self.searchbox.fill(metric)
        self.search_option(metric).click()

    def check_show_service_name_checkbox(self, check: bool = True) -> None:
        if self._show_service_name_checkbox.is_checked() != check:
            self._show_service_name_checkbox.click()


class EditElementTopList(ElementTopList):
    """Represent the 'Edit element: Top list' page.

    To navigate: 'Monitor -> <dashboard> -> Enter layout mode -> Edit properties of element'.
    """

    page_title = "Edit element: Top list"


class AddElementTopList(ElementTopList):
    """Represent the 'Add element: Top list' page.

    To navigate: 'Monitor -> <dashboard> -> Add - Top list'.
    """

    page_title = "Add element: Top list"
