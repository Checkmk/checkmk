#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
import time
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page
from playwright.sync_api import TimeoutError as PWTimeoutError

from tests.gui_e2e.testlib.api_helpers import LOCALHOST_IPV4
from tests.gui_e2e.testlib.host_details import HostDetails
from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


class SetupHost(CmkPage):
    """Represent the page `setup -> Hosts`."""

    @override
    def navigate(self) -> None:
        """Instructions to navigate to `setup -> Hosts` page.

        This method is used within `CmkPage.__init__`.
        """
        logger.info("Navigate to 'Setup hosts' page")
        self.main_menu.setup_menu("Hosts").click()
        _url_pattern: str = quote_plus("wato.py?mode=folder")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Setup hosts' page")
        expect(self.get_link("Add host")).to_be_visible()
        expect(self.get_link("Add folder")).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        mapping = DropdownListNameToID()
        setattr(mapping, "Hosts", "menu_hosts")
        return mapping

    @property
    def add_host(self) -> Locator:
        return self.get_link("Add host")

    @property
    def add_folder(self) -> Locator:
        return self.get_link("Add folder")

    def _host_row(self, host_name: str) -> Locator:
        return self.main_area.locator(f"tr:has(td:has-text('{host_name}'))")

    def perform_action_on_host(self, host_name: str, action: str) -> None:
        """Perform an action on a host using the 'actions menu' / 'burger menu'.

        Example of such an action,
        + 'Clone host'
        + 'Detect network parents'
        """
        host_row = self._host_row(host_name)
        self.action_menu_button(host_name).click()
        logger.info("Perform '%s' on the host: '%s' using 'burger menu'.", action, host_name)
        host_row.locator("div#popup_menu").get_by_text(action).click()

    def action_menu_button(self, host_name: str) -> Locator:
        """Locator to the burger / action menu corresponding to a host."""
        return self._host_row(host_name).get_by_role("link", name="Open the host action menu")

    def effective_parameters_button(self, host_name: str) -> Locator:
        return self._host_row(host_name).get_by_role("link", name="View the rule based effective")

    @property
    def successfully_deleted_msg(self) -> Locator:
        return self.main_area.locator().get_by_text("Successfully deleted", exact=False)

    def select_hosts(self, host_names: list[str]) -> None:
        for host_name in host_names:
            self._host_row(host_name).locator("label").click()

    def delete_selected_hosts(self) -> None:
        logger.info("Delete selected hosts")
        self.main_area.click_item_in_dropdown_list(dropdown_button="Hosts", item="Delete hosts")
        self.main_area.locator().get_by_role(role="button", name="Delete").click()
        try:
            expect(
                self.successfully_deleted_msg,
                message="Expected message 'Successfully deleted X hosts' to be visible!",
            ).to_be_visible()
        except PWTimeoutError as e:
            if self.main_area.locator("div.error").count() != 0:
                error_msg = (
                    f"The following error appears in the UI:\n {self.main_area.get_error_text()}"
                )
                e.add_note(error_msg)
            raise e

    def folder_icon(self, folder_id: str) -> Locator:
        return self.main_area.locator(f"#folder_{folder_id}")

    def action_icon_for_host(self, host_name: str, icon_name: str) -> Locator:
        """Return web-element corresponding to an actionable icon present in the host's row.

        Args:
            host_name (str): Name of the host.
            icon_name (str): Name of the icon, which perfoms an action on the host.
        """
        return self._host_row(host_name).get_by_role("link", name=icon_name)

    def delete_folder(self, folder_id: str) -> None:
        """Delete a folder by its id.

        Deleting a folder requires the user to hover over the top part of the folder to reveal the
        action buttons. The user then clicks on the delete button and confirms the deletion.
        The folder ID is in most cases the folder name.
        """
        logger.info("Delete folder: %s", folder_id)
        # All folders have an id of the form `folder_<folder_id>`
        # The div with the hoverarea class contains the action buttons (and reacts to hover)
        buttons = self.folder_icon(folder_id).locator("div.hoverarea")
        expect(
            buttons, message=f"Expected folder ID '{folder_id}' to be uniquely present"
        ).to_have_count(1)
        buttons.hover()
        buttons.get_by_role("link", name="Delete this folder").click()
        self.main_area.locator().get_by_role("button", name="Delete").click()


class AddHost(CmkPage):
    """Represents page `setup -> Hosts -> Add host`."""

    page_title: str = "Add host"

    dropdown_buttons: list[str] = [
        "Host",
        "Display",
        "Help",
    ]

    suggestions: list[str] = [
        r"Save & run service discovery",
        r"Save & view folder",
        r"Save & run connection tests",
    ]

    properties: list[str] = [
        r"Basic settings",
        r"Network address",
        r"Monitoring agents",
        r"Custom attributes",
        r"Management board",
    ]

    @override
    def navigate(self) -> None:
        """Instructions to navigate to `Setup -> Hosts -> Add host` page."""
        setup_host_page = SetupHost(self.page)
        logger.info("Navigate to '%s' page", self.page_title)
        setup_host_page.add_host.click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?folder=&mode=newhost")), wait_until="load"
        )
        self.validate_page()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def host_name_text_field(self) -> Locator:
        return self.main_area.get_input("host")

    @property
    def monitored_on_site_checkbox(self) -> Locator:
        return self.main_area.get_attribute_label("site")

    @property
    def monitored_on_site_dropdown_button(self) -> Locator:
        return self.main_area.locator("div#attr_entry_site >> b")

    @property
    def ipv4_address_checkbox(self) -> Locator:
        return self.main_area.get_attribute_label("ipaddress")

    @property
    def ipv4_address_text_field(self) -> Locator:
        return self.main_area.get_input("ipaddress")

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.main_area.get_suggestion(self.suggestions[0])).to_be_visible()
        expect(self.host_name_text_field).to_be_visible()

    @property
    def agent_and_api_integration_checkbox(self) -> Locator:
        return (
            self.main_area.locator()
            .get_by_role("cell", name="Checkmk agent / API")
            .locator("label")
        )

    @property
    def agent_and_api_integration_dropdown_button(self) -> Locator:
        return self.main_area.locator("div#attr_entry_tag_agent >> b")

    @property
    def snmp_checkbox(self) -> Locator:
        return self.main_area.locator().get_by_role("cell", name="SNMP").locator("label")

    @property
    def snmp_dropdown_button(self) -> Locator:
        return self.main_area.locator("div#attr_entry_tag_snmp_ds >> b")

    def create_host(self, host: HostDetails, test_site: Site | None = None) -> None:
        """On `Setup -> Hosts -> Add host` page, create a new host and activate changes.

        Note: only host name and ip address are filled in this method. If needed the method can
        be extended to fill other parameters of the host.
        """
        logger.info("Fill in host details")
        self.host_name_text_field.fill(host.name)

        if host.site:
            self.monitored_on_site_checkbox.click()
            self.monitored_on_site_dropdown_button.click()
            self.main_area.locator().get_by_role("option").filter(has_text=host.site).click()

        self.ipv4_address_checkbox.click()
        self.ipv4_address_text_field.fill(host.ip if host.ip else LOCALHOST_IPV4)

        if host.agent_and_api_integration:
            self.agent_and_api_integration_checkbox.click()
            self.agent_and_api_integration_dropdown_button.click()
            self.main_area.locator().get_by_role(
                "option", name=host.agent_and_api_integration
            ).click()

        if host.snmp:
            self.snmp_checkbox.click()
            self.snmp_dropdown_button.click()
            self.main_area.locator().get_by_role("option", name=host.snmp).click()

        logger.info("Save new host")
        self.main_area.get_suggestion("Save & view folder").click()
        try:
            self.page.wait_for_url(
                url=re.compile(quote_plus("wato.py?folder=&mode=folder")), wait_until="load"
            )
        except Exception as e:
            if self.main_area.locator("div.error").count() != 0:
                error_msg = (
                    f"The following error appears in the UI:\n {self.main_area.get_error_text()}"
                )
                e.add_note(error_msg)
            raise e
        self.activate_changes(test_site)


class HostProperties(CmkPage):
    """Represents page `setup -> Hosts -> <host name> properties`."""

    dropdown_buttons: list[str] = [
        "Host",
        "Display",
        "Help",
    ]

    # Text of links seen on GUI
    links: list[str] = [
        r"Save & run service discovery",
        r"Save & view folder",
        r"Save & run connection tests",
        r"Update site DNS cache",
    ]

    properties: list[str] = [
        r"Monitoring agents",
        r"Custom attributes",
        r"Management board",
        r"Creation / Locking",
    ]

    def __init__(
        self,
        page: Page,
        host: HostDetails,
        exists: bool = False,
        navigate_to_page: bool = True,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        self.details = host
        self._exists = exists
        self.page_title = f"Properties of host {host.name}"
        super().__init__(
            page=page,
            navigate_to_page=navigate_to_page,
            timeout_assertions=timeout_assertions,
            timeout_navigation=timeout_navigation,
        )

    @override
    def navigate(self) -> None:
        """Instructions to navigate to `setup -> Hosts -> <host name> properties` page.

        This method is used within `CmkPage.__init__`.
        """
        if not self._exists:
            add_host_page = AddHost(self.page)
            add_host_page.create_host(self.details)
            self._exists = True
        setup_host_page = SetupHost(self.page)
        logger.info("Navigate to 'Host properties' page")
        setup_host_page.get_link(self.details.name).click()
        _url_pattern = quote_plus(f"wato.py?folder=&host={self.details.name}&mode=edit_host")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Host properties' page")
        self.main_area.check_page_title(self.page_title)
        expect(self.main_area.get_text(text=HostProperties.dropdown_buttons[0])).to_be_visible()
        expect(self.main_area.get_text(text=HostProperties.links[0])).to_be_visible()
        expect(self.main_area.get_text(text=HostProperties.properties[0])).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        mapping = DropdownListNameToID()
        setattr(mapping, "Host", "menu_host")
        return mapping

    def delete_host(self, test_site: Site | None = None) -> None:
        """On `setup -> Hosts -> Properties`, delete host and activate changes."""
        logger.info("Delete host: %s", self.details.name)
        self.main_area.click_item_in_dropdown_list(dropdown_button="Host", item="Delete")
        self.main_area.locator().get_by_role(role="button", name="Delete").click()
        # TODO - validate something meaningful
        # Force serialization of pages being navigated to by introducing a delay.
        # self.page.wait_for_url(
        #     url=re.compile(quote_plus("wato.py?folder=&mode=folder")), wait_until="load"
        # )
        time.sleep(0.5)
        self.activate_changes(test_site)
        self._exists = False
