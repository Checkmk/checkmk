#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

"""This test module verifies the activating of pending changes through the "Changes" slideout
of main menu.
"""

import logging
from collections.abc import Iterator

import pytest
from faker import Faker
from playwright.sync_api import expect

from tests.gui_e2e.testlib.api_helpers import LOCALHOST_IPV4
from tests.gui_e2e.testlib.host_details import AddressFamily, AgentAndApiIntegration, HostDetails
from tests.gui_e2e.testlib.playwright.pom.changes.activate_changes import ActivateChangesSlideout
from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.gui_e2e.testlib.playwright.pom.setup.hosts import AddHost, HostProperties
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


def _create_bulk_hosts(site: Site, num_hosts: int, test_site: Site) -> Iterator:
    """Helper function to create hosts in bulk on the specified site.
    Args:
        site: The test site where hosts will be created. Could be central or remote.
        num_hosts: Number of hosts to create.
        test_site: The fixture for central test site.
    """
    faker = Faker()

    hosts_list = [faker.unique.hostname() for _ in range(num_hosts)]
    entries = [
        {
            "host_name": host,
            "folder": "/",
            "attributes": {"ipaddress": LOCALHOST_IPV4, "site": site.id},
        }
        for host in hosts_list
    ]

    created_hosts = test_site.openapi.hosts.bulk_create(entries=entries, bake_agent=False)

    yield created_hosts

    test_site.openapi.hosts.bulk_delete([host["id"] for host in created_hosts])
    test_site.openapi.changes.activate_and_wait_for_completion()


@pytest.fixture(name="bulk_create_hosts_central_site")
def _bulk_create_hosts_central_site(request: pytest.FixtureRequest, test_site: Site) -> Iterator:
    """Create hosts in bulk on test_site, parametrized by number."""
    num_hosts = int(request.param)
    yield from _create_bulk_hosts(test_site, num_hosts, test_site)


@pytest.fixture(name="bulk_create_hosts_remote_site")
def _bulk_create_hosts_remote_site(
    request: pytest.FixtureRequest, remote_site: Site, test_site: Site
) -> Iterator:
    """Create hosts in bulk on remote_site, parametrized by number."""
    num_hosts = int(request.param)
    yield from _create_bulk_hosts(remote_site, num_hosts, test_site)


def test_activate_changes_slideout_one_change(
    dashboard_page: MainDashboard, test_site: Site
) -> None:
    """Check elements of 'Activate changes' slideout with none and one change"""
    slideout = ActivateChangesSlideout(dashboard_page)

    logger.info("Validate elements of the slideout without changes")
    expect(
        slideout.no_pending_changes_text, "The banner 'No pending changes' is not visible!"
    ).to_be_visible()
    expect(slideout.info_text, "The info banner is not visible!").to_be_visible()
    slideout.info_close_btn.click()
    slideout.close()

    try:
        logger.info("Create a change with new host")
        host_details = HostDetails(
            name="delete_me",
            agent_and_api_integration=AgentAndApiIntegration.no_agent,
            address_family=AddressFamily.ip_v4_only,
        )
        add_host_page = AddHost(dashboard_page.page)
        add_host_page.create_host(host_details, test_site, activate_changes=False)

        logger.info("Validate elements of the slideout")
        slideout = ActivateChangesSlideout(dashboard_page)
        expect(slideout.info_text, "The info banner is still visible!").not_to_be_visible()
        expect(
            slideout.activate_changes_btn, "The 'Activate pending changes' button is not enabled!"
        ).to_be_enabled()
        expect(slideout.sites_section, "The 'Sites' section is not visible!").to_be_visible()
        expect(slideout.changes_section, "The 'Changes' section is not visible!").to_be_visible()
        central_site_entry = slideout.site_entry(test_site.id)
        expect(
            central_site_entry, f"An item for {test_site.id} site is not visible!"
        ).to_be_visible()
        expect(
            slideout.site_online_status(central_site_entry),
            f"Status of '{test_site.id}' site is not online!",
        ).to_be_visible()
        assert slideout.site_changes_count(central_site_entry) == 1, (
            f"The number of changes for {test_site.id} is not correct!"
        )
    finally:
        host_properties = HostProperties(dashboard_page.page, host_details, exists=True)
        host_properties.delete_host(test_site, activate=False)
        slideout = ActivateChangesSlideout(dashboard_page)
        slideout.activate_changes_strict(2)


@pytest.mark.parametrize("bulk_create_hosts_central_site", [100], indirect=True)
def test_activate_changes_slideout_bulk_changes(
    dashboard_page: MainDashboard, test_site: Site, bulk_create_hosts_central_site: None
) -> None:
    """Check elements of 'Activate changes' slideout with multiple changes on central site"""
    slideout = ActivateChangesSlideout(dashboard_page)

    expect(slideout.no_pending_changes_text).not_to_be_visible()
    if slideout.info_text.is_visible():
        slideout.info_close_btn.click()

    expect(
        slideout.activate_changes_btn, "The 'Activate pending changes' button is not enabled!"
    ).to_be_enabled()
    assert slideout.changes_section.evaluate("el => getComputedStyle(el).overflow") == "auto", (
        "Changes section is not scrollable!"
    )
    central_site_entry = slideout.site_entry(test_site.id)
    expect(central_site_entry, f"An item for {test_site.id} site is not visible!").to_be_visible()
    expect(
        slideout.site_online_status(central_site_entry),
        f"Status of '{test_site.id}' site is not online!",
    ).to_be_visible()
    assert slideout.site_changes_count(central_site_entry) == 100, (
        f"The number of changes for {test_site.id} is not correct!"
    )
    slideout.activate_changes_strict(expected_changes=100)


@pytest.mark.parametrize("bulk_create_hosts_central_site", [10], indirect=True)
@pytest.mark.parametrize("bulk_create_hosts_remote_site", [20], indirect=True)
def test_activate_changes_slideout_distributed_setup(
    dashboard_page: MainDashboard,
    test_site: Site,
    remote_site: Site,
    bulk_create_hosts_central_site: None,
    bulk_create_hosts_remote_site: None,
) -> None:
    """Check functionality of 'Activate changes' slideout in distributed setup"""
    slideout = ActivateChangesSlideout(dashboard_page)
    expect(slideout.activate_changes_btn).to_be_enabled()
    logger.info("Check that both sites are visible in the slideout")
    central_site_entry = slideout.site_entry(test_site.id)
    expect(
        central_site_entry, f"An item for central site '{test_site.id}' is not visible!"
    ).to_be_visible()
    expect(
        slideout.site_online_status(central_site_entry),
        f"Status of central site '{test_site.id}' is not online!",
    ).to_be_visible()
    assert slideout.site_changes_count(central_site_entry) == 10, (
        f"The number of changes for central site '{test_site.id}' is not correct!"
    )
    assert slideout.is_site_entry_selected(central_site_entry), (
        f"The site entry for central site '{test_site.id}' is not selected!"
    )

    remote_site_entry = slideout.site_entry(site_name=remote_site.id, central=False)
    expect(
        remote_site_entry, f"An item for remote site '{remote_site.id}' is not visible!"
    ).to_be_visible()
    expect(
        slideout.site_online_status(remote_site_entry),
        f"Status of remote site '{remote_site.id}' is not online!",
    ).to_be_visible()
    assert slideout.site_changes_count(remote_site_entry) == 20, (
        f"The number of changes for remote site '{remote_site.id}' is not correct!"
    )
    assert slideout.is_site_entry_selected(remote_site_entry), (
        f"The site entry for remote site '{remote_site.id}' is not selected!"
    )

    logging.info("Check that total changes label is visible with correct text")
    expect(slideout.total_changes_lbl, "The 'Total changes' label is not visible!").to_be_visible()
    count = slideout.total_changes_count()
    assert count == 30, f"The number of total changes is not correct! Shown: {count}, Expected: 30"

    logging.info("Check that foreign changes label is visible with correct text")
    expect(
        slideout.foreign_changes_lbl, "The 'Foreign changes' label is not visible!"
    ).to_be_visible()
    count = slideout.foreign_changes_count()
    # All changes were made by other user 'not_automation' via API
    assert count == 30, (
        f"The number of foreign changes is not correct! Shown: {count}, Expected: 30"
    )

    logging.info("Deselect remote site")
    slideout.site_entry_checkbox(remote_site_entry).click()
    assert not slideout.is_site_entry_selected(remote_site_entry), (
        f"The site entry for remote site '{remote_site.id}' is still selected!"
    )
    logging.info("Activate changes only for central site")
    slideout.activate_changes_strict(expected_changes=10)

    logging.info("Now activate changes for remote site")
    expect(slideout.activate_changes_btn).to_be_enabled()
    expect(slideout.total_changes_lbl).to_have_text("Changes: (20)")
    assert slideout.is_site_entry_selected(remote_site_entry), (
        f"The site entry for remote site '{remote_site.id}' is not selected!"
    )
    slideout.activate_changes_strict(expected_changes=20)
