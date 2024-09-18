#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time

import pytest
from faker import Faker
from playwright.sync_api import expect

from tests.testlib.host_details import AgentAndApiIntegration, HostDetails, SNMP
from tests.testlib.playwright.pom.dashboard import Dashboard
from tests.testlib.playwright.pom.monitor.service_search import ServiceSearchPage

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "created_host",
    [
        pytest.param(
            HostDetails(
                name=f"test_host_{Faker().first_name()}",
                ip="127.0.0.1",
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
    dashboard_page.main_menu.monitor_menu("Service search").click()
    service_search_page = ServiceSearchPage(dashboard_page.page)

    logger.info("Apply filters and wait for the table to load")
    service_search_page.apply_filters_button.click()
    expect(service_search_page.services_table).to_be_visible()

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
    services_count = service_search_page.service_rows.count()
    assert services_count == 1, "Unexpected number of services in the table"
    time_since_last_check = service_search_page.checked_column_cells.all_inner_texts()
    (number, unit) = time_since_last_check[0].split()
    assert unit == "ms" or (
        unit == "s" and float(number) < sleep_time
    ), "Service was not rescheduled"
