import logging
from enum import StrEnum
from typing import Generic, TypeVar

from playwright.sync_api import expect, Locator

logger = logging.getLogger(__name__)


class DropdownOptions(StrEnum):
    """Represent the base type for the options of a dropdown menu."""


TDropdownOptions = TypeVar("TDropdownOptions", bound=DropdownOptions)


class DropdownHelper(Generic[TDropdownOptions]):
    """Represent a dropdown menu to choose between different options defined in a StrEnum type."""

    def __init__(self, dropdown_name: str, dropdown_box: Locator, dropdown_list: Locator) -> None:
        """Initialize the dropdown menu.

        Args:
            dropdown_name: The name of the dropdown.
            dropdown_box: The locator for the dropdown box.
            dropdown_list: The locator for the dropdown list of options.
        """
        self.__dropdown_name = dropdown_name
        self.__dropdown_box = dropdown_box
        self.__dropdown_list = dropdown_list

    def select_option(self, option: TDropdownOptions) -> None:
        """Select an option from the dropdown.

        Args:
            option: The StrEnum member that represents the dropdown option to select.
        """
        logger.info("Select option '%s' in '%s' dropdown", option, self.__dropdown_name)
        self.__dropdown_box.click()
        self.__dropdown_list.wait_for(state="visible")
        self.__dropdown_list.get_by_role("option", name=option).click()
        expect(
            self.__dropdown_box,
            message=f"Option '{option}' not set in '{self.__dropdown_name}' dropdown",
        ).to_have_text(option)
