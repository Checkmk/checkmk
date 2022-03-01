#!/usr/bin/env python
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.playwright import PPage


class TestHost:
    name = "test_host"
    ip = "127.0.0.1"


class TestHosts:
    def test_create_and_delete_a_host(self, logged_in_page: PPage):
        """Creates a host and deletes it afterwards. Calling order of static methods
        is therefore essential!
        """

        self._create_host(logged_in_page)
        self._delete_host(logged_in_page)

    @staticmethod
    def _create_host(logged_in_page: PPage):
        """Creates a host by starting from a logged in page."""
        logged_in_page.goto_setup_hosts()
        logged_in_page.main_frame.get_suggestion("Add host").click()

        logged_in_page.main_frame.get_input("host").fill(TestHost.name)
        logged_in_page.main_frame.get_attribute_label("ipaddress").click()
        logged_in_page.main_frame.get_input("ipaddress").fill(TestHost.ip)

        logged_in_page.main_frame.get_suggestion("Save & go to service configuration").click()
        logged_in_page.main_frame.get_text("1 pending change").click()

        logged_in_page.activate_selected()

        logged_in_page.expect_activation_state("Success")

        logged_in_page.goto_monitoring_all_hosts()
        logged_in_page.select_host(TestHost.name)

    @staticmethod
    def _delete_host(logged_in_page: PPage):
        """Deletes the former created host by starting from a logged in page."""
        logged_in_page.goto_setup_hosts()

        logged_in_page.main_frame.get_link_from_title("Delete this host").click()

        logged_in_page.main_frame.get_text("Yes").click()
        logged_in_page.main_frame.get_text("1 pending change").click()
        logged_in_page.activate_selected()

        logged_in_page.expect_activation_state("Success")
