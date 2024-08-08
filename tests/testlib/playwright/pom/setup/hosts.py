#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from dataclasses import dataclass
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page
from playwright.sync_api import TimeoutError as PWTimeoutError

from tests.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


@dataclass
class HostDetails:
    name: str
    ip: str
    site: str | None = None
    tag_agent: str | None = None
    tag_address_family: str | None = None
    labels: dict | None = None


class SetupHost(CmkPage):
    """Represent the page `setup -> Hosts`."""

    def __init__(self, page: Page, navigate_to_page: bool = True) -> None:
        super().__init__(page, navigate_to_page)

    def navigate(self) -> None:
        """Instructions to navigate to `setup -> Hosts` page.

        This method is used within `CmkPage.__init__`.
        """
        logger.info("Navigate to 'Setup hosts' page")
        self.main_menu.setup_menu("Hosts").click()
        _url_pattern: str = quote_plus("wato.py?mode=folder")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self._validate_page()

    def _validate_page(self) -> None:
        logger.info("Validate that current page is 'Setup hosts' page")
        expect(self.get_link("Add host")).to_be_visible()
        expect(self.get_link("Add folder")).to_be_visible()

    @property
    def add_host(self) -> Locator:
        return self.get_link("Add host")

    @property
    def add_folder(self) -> Locator:
        return self.get_link("Add folder")

    def _host_row(self, host_name: str) -> Locator:
        return self.main_area.locator(f"tr:has(td:has-text('{host_name}'))")

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
        self.main_area.click_dropdown_menu_item(
            dropdown_button="Hosts", menu_id="menu_hosts", menu_item="Delete hosts"
        )
        self.main_area.locator().get_by_role(role="button", name="Delete").click()
        try:
            expect(self.successfully_deleted_msg).to_be_visible(timeout=5000)
        except PWTimeoutError as e:
            if self.main_area.locator("div.error").count() != 0:
                error_msg = (
                    f"The following error appears in the UI:\n {self.main_area.get_error_text()}"
                )
                e.add_note(error_msg)
            raise e


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

    def navigate(self) -> None:
        """Instructions to navigate to `Setup -> Hosts -> Add host` page."""
        setup_host_page = SetupHost(self.page)
        logger.info("Navigate to '%s' page", self.page_title)
        setup_host_page.add_host.click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?folder=&mode=newhost")), wait_until="load"
        )
        self._validate_page()

    @property
    def host_name_text_field(self) -> Locator:
        return self.main_area.get_input("host")

    @property
    def ipv4_address_checkbox(self) -> Locator:
        return self.main_area.get_attribute_label("ipaddress")

    @property
    def ipv4_address_text_field(self) -> Locator:
        return self.main_area.get_input("ipaddress")

    def _validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.main_area.get_suggestion(self.suggestions[0])).to_be_visible()
        expect(self.host_name_text_field).to_be_visible()

    def create_host(self, host: HostDetails) -> None:
        """On `Setup -> Hosts -> Add host` page, create a new host and activate changes.

        Note: only host name and ip address are filled in this method. If needed the method can
        be extended to fill other parameters of the host.
        """
        logger.info("Fill in host details")
        self.host_name_text_field.fill(host.name)
        self.ipv4_address_checkbox.click()
        self.ipv4_address_text_field.fill(host.ip)

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

        logger.info("Activate changes")
        self.get_link("1 change").click()
        self.activate_selected()
        self.expect_success_state()


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
        super().__init__(page, navigate_to_page, timeout_assertions, timeout_navigation)

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
        self._validate_page()

    def _validate_page(self) -> None:
        logger.info("Validate that current page is 'Host properties' page")
        self.main_area.check_page_title(self.page_title)
        expect(self.main_area.get_text(text=HostProperties.dropdown_buttons[0])).to_be_visible()
        expect(self.main_area.get_text(text=HostProperties.links[0])).to_be_visible()
        expect(self.main_area.get_text(text=HostProperties.properties[0])).to_be_visible()

    def delete_host(self) -> None:
        """On `setup -> Hosts -> Properties`, delete host and activate changes."""
        logger.info("Delete host: %s", self.details.name)
        self.main_area.click_dropdown_menu_item(
            dropdown_button="Host", menu_id="menu_host", menu_item="Delete"
        )
        self.main_area.locator().get_by_role(role="button", name="Delete").click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?folder=&mode=folder")), wait_until="load"
        )
        logger.info("Activate changes")
        self.get_link("1 change").click()
        self.activate_selected()
        self.expect_success_state()
        self._exists = False
