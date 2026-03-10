#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.dropdown import DropdownHelper, DropdownOptions
from tests.gui_e2e.testlib.playwright.pom.sidebar.base_sidebar import SidebarHelper


class RuntimeFiltersSidebar(SidebarHelper):
    """Class that represents the sidebar to filter a dashboard.

    To navigate: '{within any dashboard} > Filter'.
    """

    sidebar_title = "Runtime filters"

    @property
    @override
    def _sidebar_locator(self) -> Locator:
        """Locator property for the main area of the sidebar."""
        return self._iframe_locator.get_by_role("dialog", name="Dashboard filter")

    @property
    @override
    def sidebar_title_locator(self) -> Locator:
        """Locator property for the sidebar title."""
        return self.locator().get_by_role("heading", name=self.sidebar_title, exact=True)

    @property
    def apply_button(self) -> Locator:
        """Locator property of 'Apply' button."""
        return self.locator().get_by_role("button", name="Apply")

    @property
    def _add_filter_section(self) -> Locator:
        """Locator property of 'Add filter' section."""
        return self.locator("div.db-filter-settings__selection-container")

    @property
    def _filter_menu_entries(self) -> Locator:
        """Locator property of 'Add filter' menu entries."""
        return self._add_filter_section.locator("div.filter-menu__entries")

    @property
    def _dropdown_list(self) -> Locator:
        """Locator property of the dropdown listbox."""
        return self.locator().get_by_role("listbox")

    @property
    def dropdown_list_filter_textbox(self) -> Locator:
        """Locator property of the filter textbox inside the dropdown listbox."""
        return self._dropdown_list.get_by_role("textbox", name="filter")

    def _get_filter_menu_item(self, item_name: str, exact: bool) -> Locator:
        """Get an item from filter menu.

        Args:
            item_name: the name of the item to get.
            exact: whether the name match has to be exact or not.

        Returns:
            The locator of the filter menu item.
        """
        return self._filter_menu_entries.locator("div.filter-menu__filter-item").get_by_text(
            item_name, exact=exact
        )

    def add_filter_to_host_selection(self, filter_name: str, sub_menu: str | None = None) -> None:
        """Add filter to widget in host selection region.

        Args:
            filter_name: name of the filter to add.
            sub_menu: name of the sub-menu button to expand before clicking the filter item.
        """
        filter_menu_item = self._get_filter_menu_item(filter_name, exact=True)

        if sub_menu is not None and not filter_menu_item.is_visible():
            self._filter_menu_entries.get_by_role("button", name=sub_menu).click()
            expect(
                filter_menu_item,
                message=f"Filter menu item '{filter_name}' not visible",
            ).to_be_visible()

        filter_menu_item.click()

    def _get_filter_container(self, filter_name: str) -> Locator:
        """Get the locator of the container of a filter from 'Host selection' region.

        Args:
            filter_name: the name of the filter of the container.

        Returns:
            The locator of the filter container.
        """
        return self.locator("div.filter-container", has_text=filter_name)

    def get_filter_combobox(self, filter_name: str) -> Locator:
        """Get the locator of the combobox to set a host filter for the widget.

        Args:
            filter_name: the name of the filter that is set by the combobox.

        Returns:
            The locator of the combobox.
        """
        return self._get_filter_container(filter_name).get_by_role("combobox")

    def select_dropdown_option[T: DropdownOptions](
        self,
        dropdown_name: str,
        dropdown: Locator,
        option: T,
        text_input: Locator | None = None,
        expected_value: str | None = None,
    ) -> None:
        """Select a dropdown option from a combobox of the sidebar.

        Args:
            dropdown_name: the name of the dropdown for debugging.
            dropdown: the locator of the dropdown.
            option: the option to select.
            text_input: the text input locator if search to filter options will be made.
            expected_value: the expected value of the dropdown after selection, for validation.
                If None, it will be validated with the option value.
        """
        dropdown_helper = DropdownHelper[T](
            dropdown_name=dropdown_name,
            dropdown_box=dropdown,
            dropdown_list=self._dropdown_list,
            text_input_filter=text_input,
        )
        dropdown_helper.select_option(
            option,
            search=(text_input is not None),
            expected_value=expected_value,
        )
