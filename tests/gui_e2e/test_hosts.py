#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from collections.abc import Iterator
from urllib.parse import quote_plus

import pytest
from faker import Faker
from playwright.sync_api import expect

from tests.gui_e2e.testlib.host_details import (
    AddressFamily,
    AgentAndApiIntegration,
    HostDetails,
)

from tests.testlib.playwright.pom.dashboard import Dashboard
from tests.testlib.playwright.pom.monitor.host_search import HostSearch
from tests.testlib.playwright.pom.monitor.host_status import HostStatus
from tests.testlib.playwright.pom.setup.hosts import HostProperties
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="host")
def fixture_host(dashboard_page: Dashboard) -> Iterator[HostProperties]:
    _host = HostProperties(
        dashboard_page.page,
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


def test_create_and_delete_a_host(dashboard_page: Dashboard) -> None:
    """Validate creation and deletes of a host."""
    # create Host
    host = HostProperties(
        dashboard_page.page,
        host=HostDetails(name=f"test_host_{Faker().first_name()}", ip="127.0.0.1"),
    )
    # validate
    host.main_menu.monitor_all_hosts.click()
    host.page.wait_for_url(url=re.compile(quote_plus("view_name=allhost")), wait_until="load")
    host.select_host(host.details.name)
    # Cleanup: delete host
    host.navigate()
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


@pytest.fixture(name="hosts_with_labels")
def create_and_delete_hosts_with_labels(test_site: Site) -> Iterator[tuple[list[HostDetails], str]]:
    site = test_site
    label_key = "label_key"
    label_value_foo = "foo"
    label_value_bar = "bar"
    foo_label_hosts = []
    bar_label_hosts = []
    faker = Faker()

    logger.info("Create hosts with labels via API")
    for i in range(8):
        host_details = HostDetails(
            name=f"test_host_{faker.unique.first_name()}",
            ip="127.0.0.1",
            site=site.id,
            agent_and_api_integration=AgentAndApiIntegration.no_agent,
            address_family=AddressFamily.ip_v4_only,
        )
        if i % 2 == 0:
            host_details.labels = {label_key: label_value_foo}
            foo_label_hosts.append(host_details)
        else:
            host_details.labels = {label_key: label_value_bar}
            bar_label_hosts.append(host_details)
        test_site.openapi.hosts.create(
            host_details.name,
            attributes=host_details.rest_api_attributes(),
        )
    site.activate_changes_and_wait_for_core_reload()

    yield foo_label_hosts, f"{label_key}:{label_value_foo}"

    logger.info("Delete all hosts via API")
    for host in foo_label_hosts + bar_label_hosts:
        site.openapi.hosts.delete(host.name)
    site.activate_changes_and_wait_for_core_reload()


def test_filter_hosts_with_host_labels(
    hosts_with_labels: tuple[list[HostDetails], str], dashboard_page: Dashboard
) -> None:
    expected_hosts_list, expected_label = hosts_with_labels
    host_status_page = HostStatus(dashboard_page.page, expected_hosts_list[0])

    host_status_page.host_label(expected_label).click()
    host_search_page = HostSearch(host_status_page.page, navigate_to_page=False)

    host_search_page.check_label_filter_applied("is", expected_label)

    # TODO: add validation corresponding to CMK-18579, if required.
    assert host_search_page.found_hosts.count() == len(
        expected_hosts_list
    ), "Unexpected number of hosts after applying label filter."
    assert sorted(host_search_page.found_hosts.all_inner_texts()) == sorted(
        [host.name for host in expected_hosts_list]
    ), "Unexpected host names after applying label filter."
