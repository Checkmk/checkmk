#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import NamedTuple, override
from urllib.parse import quote_plus

from playwright.sync_api import Locator, Page

from tests.testlib.playwright.pom.page import CmkPage


class HostDetails(NamedTuple):
    # extend as new test-cases are added
    name: str
    ip: str


class SetupHost(CmkPage):
    "Represent the page `setup -> Hosts`."

    def navigate(self) -> str:
        """Instructions to navigate to `setup -> Hosts` page.

        This method is used within `CmkPage.__init__`.
        """
        # navigate to "setup -> Hosts"
        self.main_menu.setup_menu("Hosts").click()
        # wait for page to load
        _url_pattern: str = quote_plus("wato.py?mode=folder")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        return self.page.url

    @property
    def add_host(self) -> Locator:
        return self.get_link("Add host")

    @property
    def add_folder(self) -> Locator:
        return self.get_link("Add folder")

    def create_host(self, host: HostDetails) -> None:
        """On `setup -> Hosts` page, createa a new host and activate changes."""
        # add host
        self.add_host.click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?folder=&mode=newhost")), wait_until="load"
        )
        # fill details
        self.main_area.get_input("host").fill(host.name)
        self.main_area.get_attribute_label("ipaddress").click()
        self.main_area.get_input("ipaddress").fill(host.ip)
        # save host
        self.main_area.get_suggestion("Save & view folder").click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?folder=&mode=folder")), wait_until="load"
        )
        # activate changes
        self.get_link("1 change").click()
        self.activate_selected()
        self.expect_success_state()


class HostProperties(SetupHost):
    "Represents page `setup -> Hosts -> <host name> properties`."

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
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        self.details = host
        super().__init__(page, timeout_assertions, timeout_navigation)

    def navigate(self) -> str:
        """Instructions to navigate to `setup -> Hosts -> <host name> properties` page.

        This method is used within `CmkPage.__init__`.
        """
        _ = super().navigate()
        # host doesn't exist
        self.create_host()
        # to host properties
        self.get_link(self.details.name).click()
        _url_pattern = quote_plus(f"wato.py?folder=&host={self.details.name}&mode=edit_host")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        return self.page.url

    @override
    def create_host(self, __: HostDetails | None = None) -> None:
        """Creates a host.

        ONLY if the host is not listed within `setup -> Hosts` page.
        """
        if self.get_link(self.details.name).count() == 0:
            super().create_host(self.details)
            _ = super().navigate()

    def delete_host(self) -> None:
        """On `setup -> Hosts -> Properties`, delete host and activate changes."""
        self.dropdown_button("Host").click()
        self.get_link("Delete").click()
        self.main_area.locator().get_by_role(role="button", name="Delete").click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?folder=&mode=folder")), wait_until="load"
        )
        self.get_link("1 change").click()
        self.activate_selected()
        self.expect_success_state()
