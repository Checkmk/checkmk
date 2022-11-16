#!/usr/bin/env python
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from time import time

from tests.testlib.playwright.helpers import PPage


class TestHost:
    def __init__(self, timestamp: float) -> None:
        self.name = f"test_host_{timestamp}"
        self.ip = "127.0.0.1"


class TestHosts:
    def test_create_and_delete_a_host(self, logged_in_page: PPage, is_chromium: bool) -> None:
        """Creates a host and deletes it afterwards. Calling order of static methods
        is therefore essential!
        """
        host = TestHost(round(time(), 2))
        self._create_host(logged_in_page, host)

        logged_in_page.goto_monitoring_all_hosts()
        logged_in_page.select_host(host.name)

        self._delete_host(logged_in_page, host)

    def test_reschedule(self, logged_in_page: PPage, is_chromium: bool) -> None:
        """reschedules a check"""
        host = TestHost(round(time(), 2))
        self._create_host(logged_in_page, host)

        logged_in_page.goto_monitoring_all_hosts()
        logged_in_page.select_host(host.name)

        # Use the Check_MK Service. It is always there and the first.
        # There are two Services containing "Check_MK", using the first
        logged_in_page.main_area.locator(
            "tr.data:has-text('Check_MK') >> nth=0 >> img[title='Open the action menu']"
        ).click()
        logged_in_page.main_area.locator("div#popup_menu >> a:has-text('Reschedule check')").click()
        # In case of a success the page is reloaded, therefore the div is hidden,
        # otherwise the div stays open...
        logged_in_page.main_area.locator("div#popup_menu").wait_for(state="hidden")

        self._delete_host(logged_in_page, host)

    @staticmethod
    def _create_host(logged_in_page: PPage, host: TestHost) -> None:
        """Creates a host by starting from a logged in page."""
        logged_in_page.goto_setup_hosts()
        logged_in_page.main_area.get_suggestion("Add host").click()

        logged_in_page.main_area.get_input("host").fill(host.name)
        logged_in_page.main_area.get_attribute_label("ipaddress").click()
        logged_in_page.main_area.get_input("ipaddress").fill(host.ip)

        logged_in_page.main_area.get_suggestion("Save & go to service configuration").click()
        logged_in_page.main_area.get_element_including_texts(
            element_id="changes_info", texts=["1", "change"]
        ).click()

        logged_in_page.activate_selected()
        logged_in_page.expect_success_state()

    @staticmethod
    def _delete_host(logged_in_page: PPage, host: TestHost) -> None:
        """Deletes the former created host by starting from a logged in page."""
        logged_in_page.goto_setup_hosts()

        # click on "delete host" for the given hostname via xpath selector
        logged_in_page.main_area.locator(
            f"//*[contains(@href,'delete_host%3D{host.name}')]"
        ).click()

        logged_in_page.main_area.get_text("Yes").click()
        logged_in_page.main_area.get_element_including_texts(
            element_id="changes_info", texts=["1", "change"]
        ).click()

        logged_in_page.activate_selected()
        logged_in_page.expect_success_state()
