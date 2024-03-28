#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import NamedTuple
from urllib.parse import quote_plus

from playwright.sync_api import Locator, Page

from tests.testlib.playwright.pom.navigation import CmkPage


class HostDetails(NamedTuple):
    # extend as new test-cases are added
    name: str
    ip: str


class SetupHost(CmkPage):
    "Represent the page 'setup -> Hosts'."

    def __init__(
        self,
        page: Page,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        super().__init__(page, timeout_assertions, timeout_navigation)
        self._url_pattern: str = quote_plus("wato.py?mode=folder")
        # navigate to "setup -> Hosts"
        self.main_menu.setup_menu("Hosts").click()
        # wait for page to load
        self.page.wait_for_url(url=re.compile(self._url_pattern), wait_until="load")
        self.url = self.page.url

    @property
    def add_host(self) -> Locator:
        return self.get_link("Add host")

    @property
    def add_folder(self) -> Locator:
        return self.get_link("Add folder")

    def popup_menu(self, name: str, exact: bool = True) -> Locator:
        return self.main_area.locator().get_by_role(role="heading", name=name, exact=exact)

    def create_host(self, host: HostDetails) -> None:
        """On `setup -> Hosts` page, createa a new host and activate changes."""
        self.main_menu.setup_menu("Hosts").click()
        self.add_host.click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?folder=&mode=newhost")), wait_until="load"
        )
        self.main_area.get_input("host").fill(host.name)
        self.main_area.get_attribute_label("ipaddress").click()
        self.main_area.get_input("ipaddress").fill(host.ip)
        self.main_area.get_suggestion("Save & view folder").click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?folder=&mode=folder")), wait_until="load"
        )
        self.get_link("1 change").click()
        self.activate_selected()
        self.expect_success_state()


class HostProperties(SetupHost):
    "Represents page 'setup -> Hosts -> <host name>'"

    def __init__(
        self,
        page: Page,
        host: HostDetails,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        super().__init__(page, timeout_assertions, timeout_navigation)
        self._url_pattern = quote_plus(f"wato.py?folder=&host={host.name}&mode=edit_host")
        self.details = host
        # navigate to host properties
        if self.get_link(host.name).is_hidden():
            # host doesn't exist; create host
            self.create_host(host)
            # url of setup -> Hosts
            self.goto(self.url)
        self.get_link(host.name).click()
        self.page.wait_for_url(url=re.compile(self._url_pattern), wait_until="load")
        self.url = self.page.url

    def delete_host(self) -> None:
        """On `setup -> Hosts -> Properties`, delete host and activate changes."""
        self.goto(self.url)
        self.popup_menu("Host").click()
        self.get_link("Delete").click()
        self.main_area.locator().get_by_role(role="button", name="Delete").click()
        self.page.wait_for_url(
            url=re.compile(quote_plus("wato.py?folder=&mode=folder")), wait_until="load"
        )
        self.get_link("1 change").click()
        self.activate_selected()
        self.expect_success_state()
