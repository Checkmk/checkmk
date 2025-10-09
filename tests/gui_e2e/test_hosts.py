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

from tests.gui_e2e.testlib.api_helpers import create_and_delete_hosts, LOCALHOST_IPV4
from tests.gui_e2e.testlib.host_details import AddressFamily, AgentAndApiIntegration, HostDetails
from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.gui_e2e.testlib.playwright.pom.monitor.host_search import HostSearch
from tests.gui_e2e.testlib.playwright.pom.monitor.host_status import HostStatus
from tests.gui_e2e.testlib.playwright.pom.setup.hosts import (
    AddHost,
    HostProperties,
    ImportHostsViaCSVFileUpload,
    SetupHost,
)
from tests.testlib.site import Site
from tests.testlib.utils import is_cleanup_enabled

logger = logging.getLogger(__name__)


@pytest.fixture(name="host")
def fixture_host(dashboard_page: MainDashboard, test_site: Site) -> Iterator[HostProperties]:
    _host = HostProperties(
        dashboard_page.page,
        HostDetails(name=f"test_host_{Faker().first_name()}", ip=LOCALHOST_IPV4),
    )
    yield _host
    if is_cleanup_enabled():
        _host.navigate()
        _host.delete_host(test_site)


def test_navigate_to_host_properties(host: HostProperties) -> None:
    # - sanity checks
    for link in HostProperties.dropdown_buttons + HostProperties.links + HostProperties.properties:
        locator = host.main_area.get_text(text=link, first=False)
        expect(locator).to_have_count(1)

    # - check absence of errors and warnings
    expect(host.main_area.locator("div.error")).to_have_count(0)
    expect(host.main_area.locator("div.warning")).to_have_count(0)


def test_create_and_delete_a_host(dashboard_page: MainDashboard, test_site: Site) -> None:
    """Validate creation and deletes of a host."""
    # create Host
    host = HostProperties(
        dashboard_page.page,
        host=HostDetails(name=f"test_host_{Faker().first_name()}", ip=LOCALHOST_IPV4),
    )
    # validate
    host.main_menu.monitor_all_hosts.click()
    host.page.wait_for_url(url=re.compile(quote_plus("view_name=allhost")), wait_until="load")
    host.select_host(host.details.name)
    # Cleanup: delete host
    host.navigate()
    host.delete_host(test_site)


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
            ip=LOCALHOST_IPV4,
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
    hosts_with_labels: tuple[list[HostDetails], str], dashboard_page: MainDashboard
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
    dashboard_page: MainDashboard, host_to_be_deleted: list[HostDetails], test_site: Site
) -> None:
    """Validate deletion of a host using the burger menu."""
    setup_host = SetupHost(dashboard_page.page)
    main_area_locator = setup_host.main_area.locator()
    # 'pop' prevents the host from being deleted (again) in teardown of fixture
    host_details = host_to_be_deleted.pop()

    # action
    setup_host.action_icon_for_host(host_details.name, "Delete host").click()
    # validation
    expect(
        main_area_locator.get_by_role(
            "dialog", name=re.compile(f"Delete host.*{host_details.name}")
        ),
        message=f"Missing message to confirm deletion of host: {host_details.name}!",
    ).to_be_visible()
    setup_host.main_area.get_confirmation_popup_button("Delete host").click()
    expect(
        main_area_locator.get_by_text(host_details.name),
        message=f"Deleted host: '{host_details.name}' is still visible!",
    ).to_have_count(0)
    test_site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)


def test_agent_connection_test(dashboard_page: MainDashboard) -> None:
    """Validate agent connection test of a host."""
    add_host = AddHost(dashboard_page.page)
    main_area = add_host.main_area
    main_area_locator = main_area.locator()

    agent_test_button_default_tag = main_area.locator("#attr_default_tag_agent > button")
    agent_test_button_entry_tag = main_area.locator("#attr_entry_tag_agent > button")
    expect(agent_test_button_default_tag).to_be_disabled()

    add_host.host_name_text_field.fill("localhost")
    expect(agent_test_button_default_tag).not_to_be_disabled()

    agent_test_button_default_tag.click()
    warning_container = add_host.main_area.locator(".warn-container")
    expect(warning_container).to_be_visible()

    agent_download_button = main_area.locator("div.warn-button-container > button:nth-child(1)")
    agent_download_button.click()
    slideout = main_area.locator("div.cmk-vue-app.cmk-slide-in__container")
    expect(slideout).to_be_visible()

    slidout_close_button = main_area.locator(".cmk-slide-in-dialog__close")
    slidout_close_button.click()

    add_host.host_name_text_field.fill("")
    expect(agent_test_button_default_tag).to_be_visible()
    expect(agent_test_button_default_tag).to_be_disabled()

    add_host.host_name_text_field.fill("localhost")

    datasource_checkbox = main_area_locator.get_by_role("cell", name="Checkmk agent / API").locator(
        "label"
    )
    datasource_checkbox.click()

    main_area_locator.get_by_label("API integrations if").get_by_text("API integrations if").click()
    main_area_locator.get_by_role(
        "option", name="Configured API integrations and Checkmk agent"
    ).click()
    expect(agent_test_button_entry_tag).to_be_visible()
    expect(agent_test_button_entry_tag).not_to_be_disabled()

    main_area_locator.get_by_label("Configured API integrations").get_by_text(
        "Configured API integrations"
    ).click()
    main_area_locator.get_by_title("Configured API integrations,").click()
    expect(agent_test_button_entry_tag).not_to_be_visible()

    main_area_locator.get_by_label("Configured API integrations,").get_by_text(
        "Configured API integrations,"
    ).click()
    main_area_locator.get_by_title("No API integrations, no").click()
    expect(agent_test_button_entry_tag).not_to_be_visible()

    datasource_checkbox.click()
    expect(agent_test_button_default_tag).to_be_visible()
    expect(agent_test_button_default_tag).not_to_be_disabled()


def test_agent_test(dashboard_page: MainDashboard) -> None:
    """Validate agent download slideout when creating a host."""
    host_name = "localhost"
    add_host = AddHost(dashboard_page.page)
    add_host.host_name_text_field.fill(host_name)
    add_host.save_and_run_discovery()

    try:
        agent_download_dialog = dashboard_page.main_area.locator(
            ".setup-agent-download-dialog__dialog"
        )
        expect(agent_download_dialog).to_be_visible()

        agent_download_button = dashboard_page.main_area.locator(
            "div.cmk-dialog__content > div > button.cmk-button.cmk-button--variant-info"
        )
        agent_download_button.click()

        slideout = dashboard_page.main_area.locator("div.cmk-vue-app.cmk-slide-in__container")
        expect(slideout).to_be_visible()

        slideout_close_button = dashboard_page.main_area.locator(".cmk-slide-in-dialog__close")
        slideout_close_button.click()

        with dashboard_page.page.expect_popup() as popup_info:
            dashboard_page.main_area.locator(
                "button.cmk-button:has-text('Read Checkmk user guide')"
            ).click()

        docs_page = popup_info.value

        expect(docs_page).to_have_url(
            "https://docs.checkmk.com/latest/en/wato_monitoringagents.html#agents"
        )
    finally:
        if is_cleanup_enabled():
            SetupHost(dashboard_page.page).delete_hosts(host_name)


def test_ping_host(dashboard_page: MainDashboard) -> None:
    """Validate pinging of a host."""
    add_host = AddHost(dashboard_page.page)

    status_loading = add_host.main_area.locator("div.status-box.loading").get_by_role("img")
    status_invalid = add_host.main_area.locator("div.status-box.warn").get_by_role("img")
    status_valid = add_host.main_area.locator("div.status-box.ok").get_by_role("img")

    add_host.host_name_text_field.fill("foo")
    expect(status_loading).to_be_visible()
    expect(status_invalid).to_be_visible()

    add_host.host_name_text_field.fill("localhost")
    expect(status_loading).to_be_visible()
    expect(status_valid).to_be_visible()

    add_host.ipv4_address_checkbox.click()
    add_host.ipv4_address_text_field.fill("foo")
    expect(status_loading).to_be_visible()
    expect(status_invalid).to_be_visible()

    add_host.ipv4_address_text_field.fill("127.0.0.1")
    expect(status_loading).to_be_visible()
    expect(status_valid).to_be_visible()


def test_bulk_csv_upload_form(dashboard_page: MainDashboard) -> None:
    """Test adding a number of hosts via the bulk CSV upload form."""
    csv_upload_page = ImportHostsViaCSVFileUpload(dashboard_page.page)

    # Make sure we can switch between upload and textarea and the right form fields show
    csv_upload_page.switch_to_textarea()
    csv_upload_page.switch_to_upload()
    csv_upload_page.switch_to_textarea()

    csv = """
host_name#ipaddress
server01#127.0.0.1
server02#127.0.0.2
"""
    preview_page = csv_upload_page.fill_and_upload_csv(csv)

    # With initial settings, parsing won't work correctly. Confirm that:
    first_row = preview_page.main_area.locator("table.data").locator("tr").nth(0)
    expect(first_row.locator("th")).to_have_count(1)

    # Change the settings and try again
    preview_page.set_field_delimiter("#")
    preview_page.set_has_title_line(True)
    preview_page.update_preview()

    # Now we should have two proper columns.
    first_row = preview_page.main_area.locator("table.data").locator("tr").nth(0)
    expect(first_row.locator("th")).to_have_count(2)
    expect(first_row.locator("th").nth(0)).to_have_text("host_name")
    expect(first_row.locator("th").nth(1)).to_have_text("ipaddress")

    # Everything above has been non-destructive, we didn't change anything except for
    # creating a file on disk when the CSV was uploaded. Here we actually do an import
    # and create hosts. We want to undo that at the end.
    try:
        preview_page.do_import()

        # Let's make sure it actually imported the hosts
        setup_host = SetupHost(preview_page.page, navigate_to_page=False)
        setup_host.check_host_present("server01")
        setup_host.check_host_present("server02")
    finally:
        if is_cleanup_enabled():
            SetupHost(preview_page.page, navigate_to_page=False).delete_hosts(
                "server01", "server02"
            )
