#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""This test module verifies the distributed monitoring setup through the GUI."""

import os
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from playwright.sync_api import Page

from tests.gui_e2e.testlib.host_details import AddressFamily, AgentAndApiIntegration, HostDetails
from tests.gui_e2e.testlib.playwright.helpers import CmkCredentials
from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.login import LoginPage
from tests.gui_e2e.testlib.playwright.pom.monitor.all_hosts import AllHosts
from tests.gui_e2e.testlib.playwright.pom.setup.distributed_monitoring import (
    DistributedMonitoring,
)
from tests.gui_e2e.testlib.playwright.pom.setup.hosts import HostProperties
from tests.testlib.pytest_helpers.calls import exit_pytest_on_exceptions
from tests.testlib.site import Site, SiteFactory


@contextmanager
def _configure_a_host_to_be_deleted(
    dashboard_page: Dashboard, central_site: Site, remote_site: Site
) -> Iterator[HostDetails]:
    """Context Manager to configure a host to be deleted on exit.

    Args:
        dashboard_page: The Dashboard page object.
        central_site: The central site to configure the host on.
        remote_site: The remote site to configure the host for.

    Yields:
        The host details object for the host to be deleted.
    """
    host = HostDetails(
        name="delete_me",
        site=remote_site.id,
        agent_and_api_integration=AgentAndApiIntegration.no_agent,
        address_family=AddressFamily.no_ip,
    )

    host_properties = HostProperties(dashboard_page.page, host)

    try:
        yield host

    finally:
        host_properties.delete_host(central_site)


def _check_host_is_monitored_from_remote_site(
    page: Page, site: Site, credentials: CmkCredentials, host: HostDetails
) -> None:
    """Check if a host is monitored from a remote site.

    Args:
        page: The Playwright page object.
        site: The remote site to check.
        credentials: The credentials for the remote site.
        host: The host details to check.
    """
    _previous_url = page.url

    try:
        page.goto(site.internal_url, wait_until="load")

        if "login.py" in page.url:
            login_page = LoginPage(page, site.internal_url, navigate_to_page=False)
            login_page.login(credentials)

        AllHosts(page).check_host_is_present(host.name)

    finally:
        page.goto(_previous_url, wait_until="load")


@pytest.fixture(name="remote_site", scope="module")
def fixture_remote_site(
    request: pytest.FixtureRequest, site_factory: SiteFactory
) -> Iterator[Site]:
    """Return the remote Checkmk site object."""
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        yield from site_factory.get_test_site(name="remote")


@pytest.mark.skip("New and flaky test. Investigate with CMK-24264")
def test_remote_host_configuring(
    dashboard_page: Dashboard, test_site: Site, credentials: CmkCredentials, remote_site: Site
) -> None:
    """Test distributed monitoring setup and verify it creating a host.

    This test performs the following steps:
    1. Configure the remote site in the distributed monitoring setup of the central site.
    2. Activate changes and ensure the remote site is online.
    3. Add a host to the remote site from the central site.
    4. Verify that the host is being monitored from the remote site.
    5. Clean up the distributed monitoring setup by removing all site connections.
    """
    try:
        distributed_monitoring_page = DistributedMonitoring(dashboard_page.page)
        distributed_monitoring_page.add_new_connection(remote_site)
        distributed_monitoring_page.login_to_remote_site(remote_site, credentials)
        distributed_monitoring_page.check_site_online_status(remote_site.id)

        distributed_monitoring_page.activate_changes(test_site)

        distributed_monitoring_page.navigate()
        distributed_monitoring_page.check_site_online_status(remote_site.id)

        with _configure_a_host_to_be_deleted(
            dashboard_page, test_site, remote_site
        ) as host_for_remote_site:
            _check_host_is_monitored_from_remote_site(
                dashboard_page.page,
                remote_site,
                credentials,
                host_for_remote_site,
            )

    finally:
        if os.getenv("CLEANUP", "1") == "1":
            distributed_monitoring_page.navigate()
            if distributed_monitoring_page.clean_all_site_connections() > 0:
                distributed_monitoring_page.activate_changes(test_site)
