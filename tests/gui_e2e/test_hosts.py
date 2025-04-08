#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
import re
from collections.abc import Iterator
from urllib.parse import quote_plus

import pytest
from faker import Faker
from playwright.sync_api import expect

from tests.gui_e2e.testlib.common import create_and_delete_hosts
from tests.gui_e2e.testlib.host_details import AddressFamily, AgentAndApiIntegration, HostDetails
from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.monitor.host_search import HostSearch
from tests.gui_e2e.testlib.playwright.pom.monitor.host_status import HostStatus
from tests.gui_e2e.testlib.playwright.pom.setup.hosts import HostProperties, SetupHost
from tests.testlib.site import Site

logger = logging.getLogger(__name__)
pytestmark = pytest.mark.xfail(reason="CMK-22540; Flake while activating changes ...")


@pytest.fixture(name="host")
def fixture_host(dashboard_page: Dashboard) -> Iterator[HostProperties]:
    _host = HostProperties(
        dashboard_page.page,
        HostDetails(name=f"test_host_{Faker().first_name()}", ip="127.0.0.1"),
    )
    yield _host
    if int(os.getenv("CLEANUP", "1")) == 1:
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
    label_key = "label_key"
    label_value_foo = "foo"
    label_value_bar = "bar"
    foo_label_hosts = []
    bar_label_hosts = []
    faker = Faker()

    for i in range(8):
        host_details = HostDetails(
            name=f"test_host_{faker.unique.first_name()}",
            ip="127.0.0.1",
            site=test_site.id,
            agent_and_api_integration=AgentAndApiIntegration.no_agent,
            address_family=AddressFamily.ip_v4_only,
        )
        if i % 2 == 0:
            host_details.labels = {label_key: label_value_foo}
            foo_label_hosts.append(host_details)
        else:
            host_details.labels = {label_key: label_value_bar}
            bar_label_hosts.append(host_details)
    with create_and_delete_hosts(foo_label_hosts + bar_label_hosts, test_site):
        yield foo_label_hosts, f"{label_key}:{label_value_foo}"


def test_filter_hosts_with_host_labels(
    hosts_with_labels: tuple[list[HostDetails], str], dashboard_page: Dashboard
) -> None:
    expected_hosts_list, expected_label = hosts_with_labels
    host_status_page = HostStatus(dashboard_page.page, expected_hosts_list[0])

    host_status_page.host_label(expected_label).click()
    host_search_page = HostSearch(host_status_page.page, navigate_to_page=False)

    host_search_page.check_label_filter_applied("is", expected_label)

    # TODO: add validation corresponding to CMK-18579, if required.
    assert host_search_page.found_hosts.count() == len(expected_hosts_list), (
        "Unexpected number of hosts after applying label filter."
    )
    assert sorted(host_search_page.found_hosts.all_inner_texts()) == sorted(
        [host.name for host in expected_hosts_list]
    ), "Unexpected host names after applying label filter."


@pytest.fixture(name="host_to_be_deleted", scope="function")
def fixture_host_to_be_deleted(test_site: Site) -> Iterator[list[HostDetails]]:
    """Create a host using REST-API, which is deleted in the test-case."""
    hosts = []
    hosts.append(
        HostDetails(
            name="delete_me",
            site=test_site.id,
            agent_and_api_integration=AgentAndApiIntegration.no_agent,
            address_family=AddressFamily.no_ip,
        )
    )
    with create_and_delete_hosts(hosts, test_site, allow_foreign_changes=True):
        # 'hosts' is mutable; tests/fixtures using this fixture CAN adapt its value.
        yield hosts


def test_delete_host_row(
    dashboard_page: Dashboard, host_to_be_deleted: list[HostDetails], test_site: Site
) -> None:
    """Validate deletion of a host using the burger menu."""
    setup_host = SetupHost(dashboard_page.page)
    main_area = setup_host.main_area.locator()
    # 'pop' prevents the host from being deleted (again) in teardown of fixture
    host_details = host_to_be_deleted.pop()

    # action
    setup_host.perform_action_on_host(host_details.name, "Delete host")
    # validation
    expect(
        main_area.get_by_role("dialog", name=re.compile(f"Delete host.*{host_details.name}")),
        message=f"Missing message to confirm deletion of host: {host_details.name}!",
    ).to_be_visible()
    main_area.get_by_role("button", name="Remove").click()
    expect(
        main_area.get_by_text(host_details.name),
        message=f"Deleted host: '{host_details.name}' is still visible!",
    ).to_have_count(0)
    test_site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
