#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time

import pytest
from faker import Faker
from playwright.sync_api import expect

from tests.gui_e2e.testlib.api_helpers import LOCALHOST_IPV4
from tests.gui_e2e.testlib.host_details import AgentAndApiIntegration, HostDetails, SNMP
from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.monitor.combined_graph import CombinedGraphsServiceSearch
from tests.gui_e2e.testlib.playwright.pom.monitor.service_search import ServiceSearchPage

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "created_host",
    [
        pytest.param(
            HostDetails(
                name=f"test_host_{Faker().first_name()}",
                ip=LOCALHOST_IPV4,
                agent_and_api_integration=AgentAndApiIntegration.no_agent,
                snmp=SNMP.no_snmp,
            )
        )
    ],
    indirect=["created_host"],
)
def test_reschedule_active_checks(dashboard_page: Dashboard, created_host: HostDetails) -> None:
    """Test reschedule active checks.

    Create a host with a 'PING' service. Navigate to 'Service search' page and reschedule active
    checks. Check that the 'age' of the 'PING' service is updated.
    """
    host_name = created_host.name
    dashboard_page.main_menu.monitor_menu("Service search").click()
    service_search_page = ServiceSearchPage(dashboard_page.page)

    logger.info("Apply filters and wait for the table to load")
    service_search_page.filter_sidebar.apply_host_filter(host_name)
    service_search_page.filter_sidebar.apply_filters(service_search_page.services_table)

    sleep_time = 5
    logger.info("Offset 'checked' state to at least %s seconds for test validation", sleep_time)
    time.sleep(sleep_time)

    logger.info("Reschedule active checks")
    service_search_page.main_area.click_item_in_dropdown_list(
        "Commands", "Reschedule active checks"
    )
    expect(service_search_page.reschedule_active_checks_popup).to_be_visible()
    service_search_page.spread_over_minutes_textbox.fill("0")
    service_search_page.reschedule_button.click()
    expect(service_search_page.reschedule_active_checks_confirmation_window).to_be_visible()
    service_search_page.reschedule_button.click()

    logger.info("Navigate back to the Service search view")
    service_search_page.back_to_view_link.click()
    expect(service_search_page.services_table).to_be_visible()

    logger.info("Check that the service was rescheduled")
    services_count = service_search_page.service_rows(host_name).count()
    assert services_count == 1, "Unexpected number of services in the table"
    time_since_last_check = service_search_page.checked_column_cells(host_name).all_inner_texts()
    (number, unit) = time_since_last_check[0].split()
    assert unit == "ms" or (unit == "s" and float(number) < sleep_time), (
        "Service was not rescheduled"
    )


@pytest.mark.parametrize(
    "service_filter, expected_graphs",
    [
        pytest.param(
            "cpu",
            [
                "CPU load average of last minute - {host_name} - CPU load",
                "CPU utilization - {host_name} - CPU utilization",
            ],
            id="cpu_service_filter",
        ),
        pytest.param(
            "filesystem",
            [
                "Used inodes - {host_name} - sum (1 objects)",
                "Size and used space - {host_name} - sum (3 objects)",
                "Growth trend - {host_name} - sum (1 objects)",
            ],
            id="filesystem_service_filter",
        ),
    ],
)
def test_filtered_services_combined_graphs(
    dashboard_page: Dashboard,
    service_filter: str,
    expected_graphs: list[str],
    linux_hosts: list[str],
) -> None:
    """Test filtered services combined graphs.

    Navigate to 'Service search' page, apply a filter, click on
    'All metrics of same type in one graph' and check that all expected graphs are displayed.
    """
    host_name = linux_hosts[0]
    service_search_page = ServiceSearchPage(dashboard_page.page)
    service_search_page.filter_sidebar.apply_host_filter(host_name)
    service_search_page.filter_sidebar.apply_service_filter(service_filter)
    service_search_page.filter_sidebar.apply_filters(service_search_page.services_table)
    service_search_page.main_area.click_item_in_dropdown_list(
        "Services", "All metrics of same type in one graph"
    )
    combined_graphs_service_search_page = CombinedGraphsServiceSearch(
        service_search_page.page, navigate_to_page=False
    )
    for graph_title in expected_graphs:
        formatted_graph_title = graph_title.format(host_name=host_name)
        logger.info("Check that the '%s' graph is displayed correctly", formatted_graph_title)
        combined_graphs_service_search_page.check_graph_with_timeranges(formatted_graph_title)


def test_no_errors_on_combined_graphs_page(
    dashboard_page: Dashboard, linux_hosts: list[str]
) -> None:
    """Test that there are no errors on the 'Combined graphs - Service search' page."""
    service_search_page = ServiceSearchPage(dashboard_page.page)
    service_search_page.filter_sidebar.apply_last_service_state_change_filter(
        "days ago", "1", "days ago", "0"
    )
    service_search_page.filter_sidebar.apply_filters(service_search_page.services_table)
    service_search_page.main_area.click_item_in_dropdown_list(
        "Services", "All metrics of same type in one graph"
    )
    combined_graphs_service_search_page = CombinedGraphsServiceSearch(
        service_search_page.page, navigate_to_page=False
    )
    combined_graphs_service_search_page.check_no_errors()
    # TODO: uncomment this after fixing CMK-19580
    # broken_graphs_count = combined_graphs_service_search_page.broken_graph.count()
    # assert (
    #    broken_graphs_count == 0
    # ), "There are broken graphs on the 'Combined graphs - Service search' page"
