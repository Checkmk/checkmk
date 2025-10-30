#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from collections.abc import Iterator

import pytest
from faker import Faker
from playwright.sync_api import expect

from tests.gui_e2e.testlib.api_helpers import create_and_delete_hosts, LOCALHOST_IPV4
from tests.gui_e2e.testlib.host_details import AddressFamily, AgentAndApiIntegration, HostDetails
from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.monitor.bi_all_aggregations import AllAggregations
from tests.gui_e2e.testlib.playwright.timeouts import TIMEOUT_NAVIGATION
from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="enable_bi", scope="module")
def fixture_enable_bi(test_site: Site) -> Iterator[None]:
    """A fixture to enable BI module if it is disabled."""
    aggr_id = "default_aggregation"
    aggregation = test_site.openapi.bi_aggregation.get(aggregation_id=aggr_id)
    was_changed = False
    try:
        bi_disabled = aggregation["computation_options"]["disabled"]
    except KeyError as exc:
        exc.add_note("REST-API: potential change in response structure!")
        raise exc
    if bi_disabled:
        logger.info("BI module is disabled. Enabling it now.")
        aggregation["computation_options"]["disabled"] = False
        test_site.openapi.bi_aggregation.update(aggregation_id=aggr_id, body=aggregation)
        # Verify that the module is enabled
        updated_aggregation = test_site.openapi.bi_aggregation.get(aggregation_id=aggr_id)
        wait_until(
            lambda: not updated_aggregation["computation_options"]["disabled"],
            timeout=TIMEOUT_NAVIGATION,
            interval=1,
        )
        logger.info("BI module has been enabled successfully.")
        was_changed = True
    else:
        logger.warning("BI module is already enabled! Improper teardown of last test-case?")
    yield
    # Restore the original state
    if was_changed and os.getenv("CLEANUP", "1") == "1":
        logger.info("Restoring original state of BI module.")
        aggregation["computation_options"]["disabled"] = True
        test_site.openapi.bi_aggregation.update(aggregation_id=aggr_id, body=aggregation)
        logger.info("Original state of BI module has been restored.")


@pytest.fixture(name="test_host", scope="function")
def fixture_test_host(test_site: Site) -> Iterator[HostDetails]:
    faker = Faker()
    host_details = HostDetails(
        name=f"test_host_{faker.unique.first_name()}",
        ip=LOCALHOST_IPV4,
        site=test_site.id,
        agent_and_api_integration=AgentAndApiIntegration.cmk_agent,
        address_family=AddressFamily.ip_v4_only,
    )
    with create_and_delete_hosts([host_details], test_site):
        yield host_details


def test_all_aggregations_sanity(
    dashboard_page: Dashboard,
    test_host: HostDetails,
    test_site: Site,
    enable_bi: Iterator[None],
) -> None:
    """A sanity test of the elements on the `Monitor -> Business Intelligence -> All aggregations`
    page.

    The test checks for the presence and their expected values of various elements within the first
    row with host's data of the "Hosts" aggregation group.
    """
    logger.info("Navigating to 'Monitor -> Business Intelligence -> All aggregations' page")
    all_aggregations_page = AllAggregations(dashboard_page.page)
    logger.info(
        "Validate elements on the 'Monitor -> Business Intelligence -> All aggregations' page"
    )
    all_aggregations_page.check_no_errors()
    aggregation_row = all_aggregations_page.hosts_aggregation_row(index=0)
    expect(
        aggregation_row.visualize_icon, "'Visualize  this aggregation' icon not visible"
    ).to_be_visible()
    expect(
        aggregation_row.show_only_icon, "'Show only this aggregation' icon not visible"
    ).to_be_visible()
    expect(
        aggregation_row.analyse_availability_icon,
        "'Analyse availability of this aggregation' icon not visible",
    ).to_be_visible()
    assert aggregation_row.state == (
        expect_state := "CRIT"
    ), f"Expected state to be '{expect_state}'!"
    assert (
        host_name := test_host.name
    ) in aggregation_row.tree_name, f"Expected '{host_name}' to be in tree name!"
    expect(
        aggregation_row.host_link,
        message=f"Host name '{host_name}' not found in 'Hosts' column!",
    ).to_have_text(host_name)
