#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage, MainArea
from tests.system.gui.testlib.playwright.pom.setup.otel.attribute_filter_editor import (
    AttributeFilterEditor,
)

logger = logging.getLogger(__name__)


class DCD(CmkPage):
    """Represent the page 'Dynamic host management', which configures the DCD.

    Accessible at,
    Setup > Hosts > Dynamic host management
    """

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Dynamic host management' page")
        self.main_menu.setup_menu("Dynamic host management").click()
        self.page.wait_for_url(url=re.compile(re.escape("mode=dcd_connections")), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Dynamic host management' page")
        self.main_area.check_page_title("Dynamic host management")
        expect(self.add_connection_button).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def add_connection_button(self) -> Locator:
        return self.main_area.locator().get_by_role("link", name="Add connection")

    def connection_row(self, identifier: str, exact: bool = False) -> Locator:
        """Return a locator for a connection.

        The identifier should be a uniquely identifying string within a cell of the row, like the
        connection name/ID. Use `exact=True` to match the entire cell contents.
        """
        return self.main_area.locator(
            "tr.data",
            has=self.main_area.locator().get_by_role("cell", name=identifier, exact=exact),
        )


@dataclass(frozen=True)
class AttributeCondition:
    key: str
    value: str


class HostNameLookupRule:
    """One entry of the 'Telemetry Host and Service configuration' list."""

    def __init__(self, root: Locator, main_area: MainArea) -> None:
        self.root = root
        self.attribute_filter = AttributeFilterEditor(
            root.get_by_role("group", name="Attributes", exact=True),
            main_area,
            root.get_by_text("Attributes", exact=True).click,
        )

    @property
    def host_name_template_textfield(self) -> Locator:
        return self.root.get_by_role(
            "textbox", name="Host name template used to name the hosts", exact=True
        )

    def fill(self, host_name_template: str, conditions: Sequence[AttributeCondition]) -> None:
        self.host_name_template_textfield.fill(host_name_template)
        for condition in conditions:
            self.attribute_filter.add_condition(condition.key, condition.value)


class AddDCDConnection(CmkPage):
    """Represent the page 'Add connection' of the 'Dynamic host management'.

    Accessible at,
    Setup > Hosts > Dynamic host management > Add connection
    """

    page_title = "Add connection"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        DCD(self.page).add_connection_button.click()
        self.page.wait_for_url(url=re.compile(re.escape("mode=edit_dcd_connection")))
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.connector_type_dropdown).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def unique_id_textfield(self) -> Locator:
        return self.main_area.locator().get_by_label("Unique ID", exact=True)

    @property
    def title_textfield(self) -> Locator:
        return self.main_area.locator().get_by_label("Title", exact=True)

    @property
    def connector_type_dropdown(self) -> Locator:
        return self.main_area.locator().get_by_role("combobox", name="Connector type", exact=True)

    @property
    def save_button(self) -> Locator:
        return self.main_area.get_suggestion("Save")

    def select_connector_type(self, connector_type: str) -> None:
        logger.info("Select connector type '%s'", connector_type)
        self.connector_type_dropdown.click()
        self.main_area.locator().get_by_role("option", name=connector_type, exact=True).click()

    @property
    def _host_name_lookup_rules(self) -> Locator:
        return self.main_area.locator().get_by_role(
            "group", name="Telemetry Host and Service configuration", exact=True
        )

    def host_name_lookup_rule(self, index: int) -> HostNameLookupRule:
        return HostNameLookupRule(
            self._host_name_lookup_rules.get_by_role("listitem").nth(index), self.main_area
        )

    def add_host_name_lookup_rule(self) -> HostNameLookupRule:
        rules = self._host_name_lookup_rules.get_by_role("listitem")
        count = rules.count()
        logger.info("Add host name lookup rule #%d", count + 1)
        self._host_name_lookup_rules.get_by_role("button", name="Add new entry").click()
        expect(rules).to_have_count(count + 1)
        return self.host_name_lookup_rule(count)

    def save(self) -> DCD:
        """Save the connection; the GUI returns to the list of connections."""
        logger.info("Save the connection")
        self.click_and_wait_for_navigation(self.save_button, re.compile("mode=dcd_connections"))
        return DCD(self.page, navigate_to_page=False)
