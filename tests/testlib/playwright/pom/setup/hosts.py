#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import NamedTuple
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator, Page

from tests.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class HostDetails(NamedTuple):
    # extend as new test-cases are added
    name: str
    ip: str


class SetupHost(CmkPage):
    """Represent the page `setup -> Hosts`."""

    def __init__(self, page: Page, navigate_to_page: bool = True) -> None:
        super().__init__(page, navigate_to_page)

    def navigate(self) -> None:
        """Instructions to navigate to `setup -> Hosts` page.

        This method is used within `CmkPage.__init__`.
        """
        logger.info("Navigate to 'Setup hosts' page")
        # navigate to "setup -> Hosts"
        self.main_menu.setup_menu("Hosts").click()
        # wait for page to load
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

    def create_host(self, host: HostDetails) -> None:
        """On `setup -> Hosts` page, create a new host and activate changes."""
        logger.info("Creating a host: %s", host.name)
        self.add_host.click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?folder=&mode=newhost")), wait_until="load"
        )
        logger.info("Fill in host details")
        self.main_area.get_input("host").fill(host.name)
        self.main_area.get_attribute_label("ipaddress").click()
        self.main_area.get_input("ipaddress").fill(host.ip)
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
        setup_host_page = SetupHost(self.page)
        if not self._exists:
            setup_host_page.create_host(self.details)
            self._exists = True
            setup_host_page.navigate()
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
        self.dropdown_button("Host").click()
        self.get_link("Delete").click()
        self.main_area.locator().get_by_role(role="button", name="Delete").click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?folder=&mode=folder")), wait_until="load"
        )
        logger.info("Activate changes")
        self.get_link("1 change").click()
        self.activate_selected()
        self.expect_success_state()
        self._exists = False
