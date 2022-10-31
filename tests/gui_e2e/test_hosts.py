#!/usr/bin/env python
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import subprocess

import pytest

from tests.testlib.playwright.helpers import PPage
from tests.testlib.site import Site


class TestHost:
    name = "test_host"
    ip = "127.0.0.1"


class TestHosts:
    def test_create_and_delete_a_host(
        self, logged_in_page: PPage, is_chromium: bool, test_site: Site
    ) -> None:
        """Creates a host and deletes it afterwards. If the host already exists, it is deleted,
        created and re-deleted. This makes the test execution independent of the previous status.
        """
        if not is_chromium:
            pytest.skip("Test currently working with the chromium engine only.")

        if self._host_in_conf(TestHost.name, test_site.id):
            self._delete_host(logged_in_page, test_site.id)

        self._create_host(logged_in_page, test_site.id)

        logged_in_page.goto_monitoring_all_hosts()
        logged_in_page.select_host(TestHost.name)

        self._delete_host(logged_in_page, test_site.id)

    def test_reschedule(self, logged_in_page: PPage, is_chromium: bool, test_site: Site) -> None:
        """Reschedules a check."""
        if not is_chromium:
            pytest.skip("Test currently working with the chromium engine only.")

        if not self._host_in_conf(TestHost.name, test_site.id):
            self._create_host(logged_in_page, test_site.id)

        logged_in_page.goto_monitoring_all_hosts()
        logged_in_page.select_host(TestHost.name)

        # Use the Check_MK Service. It is always there and the first.
        # There are two Services containing "Check_MK", using the first
        logged_in_page.main_frame.locator(
            "tr.data:has-text('Check_MK') >> nth=0 >> img[title='Open the action menu']"
        ).click()
        logged_in_page.main_frame.locator(
            "div#popup_menu >> a:has-text('Reschedule check')"
        ).click()
        # In case of a success the page is reloaded, therefore the div is hidden,
        # otherwise the div stays open...
        logged_in_page.main_frame.locator("div#popup_menu").wait_for(state="hidden")

        self._delete_host(logged_in_page, test_site.id)

    def _create_host(self, logged_in_page: PPage, site_id: str) -> None:
        """Creates a host by starting from a logged in page."""
        logged_in_page.goto_setup_hosts()
        logged_in_page.main_frame.get_suggestion("Add host").click()

        logged_in_page.main_frame.get_input("host").fill(TestHost.name)
        logged_in_page.main_frame.get_attribute_label("ipaddress").click()
        logged_in_page.main_frame.get_input("ipaddress").fill(TestHost.ip)

        logged_in_page.main_frame.get_suggestion("Save & go to service configuration").click()
        logged_in_page.main_frame.get_element_including_texts(
            element_id="changes_info", texts=["1", "change"]
        ).click()

        logged_in_page.activate_selected()

        logged_in_page.expect_activation_state("Success")

        assert self._host_in_conf(TestHost.name, site_id)

    def _delete_host(self, logged_in_page: PPage, site_id: str) -> None:
        """Deletes the former created host by starting from a logged in page."""
        logged_in_page.goto_setup_hosts()

        logged_in_page.main_frame.get_link_from_title("Delete this host").click()

        logged_in_page.main_frame.get_text("Yes").click()
        logged_in_page.main_frame.get_element_including_texts(
            element_id="changes_info", texts=["1", "change"]
        ).click()
        logged_in_page.activate_selected()

        logged_in_page.expect_activation_state("Success")

        assert not self._host_in_conf(TestHost.name, site_id)

    @staticmethod
    def _host_in_conf(hostname: str, site_id: str) -> bool:
        """Check if the given hostname is contained in the hosts.mk file."""
        proc = subprocess.run(
            ["su", site_id],
            text=True,
            input="cat ~/etc/check_mk/conf.d/wato/hosts.mk\n",
            stdout=subprocess.PIPE,
        )

        return hostname in proc.stdout
