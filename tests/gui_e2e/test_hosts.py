#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterator
from urllib.parse import quote_plus

import pytest
from faker import Faker
from playwright.sync_api import expect

from tests.testlib.playwright.pom.login import LoginPage
from tests.testlib.playwright.pom.setup.hosts import HostDetails, HostProperties


@pytest.fixture(name="host")
def fixture_host(logged_in_page: LoginPage) -> Iterator[HostProperties]:
    _host = HostProperties(
        logged_in_page.page,
        HostDetails(name=f"test_host_{Faker().first_name()}", ip="127.0.0.1"),
    )
    yield _host
    _host.navigate()
    _host.delete_host()


def test_navigate_to_host_properties(host: HostProperties) -> None:
    # - sanity checks
    for link in HostProperties.dropdown_buttons + HostProperties.links + HostProperties.properties:
        locator = host.main_area.get_text(text=link, first=False)
        expect(locator).to_have_count(1)

    # - check absence of errors and warnings
    expect(host.main_area.locator("div.error")).to_have_count(0)
    expect(host.main_area.locator("div.warning")).to_have_count(0)


def test_create_and_delete_a_host(logged_in_page: LoginPage) -> None:
    """Validate creation and deletes of a host."""
    # create Host
    host = HostProperties(
        logged_in_page.page,
        host=HostDetails(name=f"test_host_{Faker().first_name()}", ip="127.0.0.1"),
    )
    # validate
    host.main_menu.monitor_all_hosts.click()
    host.page.wait_for_url(url=re.compile(quote_plus("view_name=allhost")), wait_until="load")
    host.select_host(host.details.name)
    # Cleanup: delete host
    _ = host.navigate()
    host.delete_host()


def test_reschedule(host: HostProperties) -> None:
    """reschedules a check"""
    host.main_menu.monitor_all_hosts.click()
    host.select_host(host.details.name)

    # Use the Check_MK Service. It is always there and the first.
    # There are two Services containing "Check_MK", using the first
    host.main_area.locator(
        "tr.data:has-text('Check_MK') >> nth=0 >> img[title='Open the action menu']"
    ).click()
    host.main_area.locator("div#popup_menu >> a:has-text('Reschedule check')").click()
    # In case of a success the page is reloaded, therefore the div is hidden,
    # otherwise the div stays open...
    host.main_area.locator("div#popup_menu").wait_for(state="hidden")
