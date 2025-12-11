#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from enum import StrEnum

from playwright.sync_api import expect, Locator

logger = logging.getLogger(__name__)


class TextInputNotProvided(Exception):
    """Exception to be raised if search option required but not text input was provided"""


class DropdownOptions(StrEnum):
    """Represent the base type for the options of a dropdown menu."""


class DropdownHelper[TDropdownOptions: DropdownOptions]:
    """Represent a dropdown menu to choose between different options defined in a StrEnum type."""

    def __init__(
        self,
        dropdown_name: str,
        dropdown_box: Locator,
        dropdown_list: Locator,
        text_input_filter: Locator | None = None,
    ) -> None:
        """Initialize the dropdown menu.

        Args:
            dropdown_name: The name of the dropdown.
            dropdown_box: The locator for the dropdown box.
            dropdown_list: The locator for the dropdown list of options.
            text_input_filter: The locator of the text input to filter options.
        """
        self.__dropdown_name = dropdown_name
        self.__dropdown_box = dropdown_box
        self.__dropdown_list = dropdown_list
        self.__text_input_filter = text_input_filter

    def __search_option(self, option: TDropdownOptions) -> None:
        if self.__text_input_filter is None:
            raise TextInputNotProvided("Text input filter locator should be provided")

        self.__text_input_filter.fill(option)

    def select_option(
        self, option: TDropdownOptions, exact: bool = True, search: bool = False
    ) -> None:
        """Select an option from the dropdown.

        Args:
            option: The StrEnum member that represents the dropdown option to select.
        """
        logger.info("Select option '%s' in '%s' dropdown", option, self.__dropdown_name)
        self.__dropdown_box.click()
        self.__dropdown_list.wait_for(state="visible")

        if search:
            self.__search_option(option)

        self.__dropdown_list.get_by_role("option", name=option, exact=exact).click()
        expect(
            self.__dropdown_box,
            message=f"Option '{option}' not set in '{self.__dropdown_name}' dropdown",
        ).to_have_text(option)
