#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re

import pytest
from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.monitor.edit_element_top_list import (
    AddElementTopList,
    EditElementTopList,
)
from tests.gui_e2e.testlib.playwright.pom.monitor.hosts_dashboard import (
    LinuxHostsDashboard,
    WindowsHostsDashboard,
)

logger = logging.getLogger(__name__)


def test_dashboard_sanity_check(dashboard_page: Dashboard) -> None:
    for dashlet_title in dashboard_page.default_dashlets_list:
        expect(dashboard_page.dashlet(dashlet_title)).to_be_visible()

    for dropdown_button_name in dashboard_page.dropdown_buttons:
        expect(dashboard_page.main_area.dropdown_button(dropdown_button_name)).to_be_visible()

    for icon_title in dashboard_page.icons_list:
        expect(dashboard_page.menu_icon(icon_title)).to_be_visible()

    expect(dashboard_page.dashlet_svg("Host statistics")).to_be_visible()
    expect(dashboard_page.dashlet_svg("Service statistics")).to_be_visible()


@pytest.mark.parametrize(
    "hosts, dashboard_class, dashlets_expected_row_count",
    [
        pytest.param(
            "linux_hosts",
            LinuxHostsDashboard,
            {
                "Host statistics": 0,
                "Service statistics": 0,
                "Total agent execution time": 0,
                "Top 10: CPU utilization": 1,
                "Top 10: Memory utilization": 1,
                "Top 10: Input bandwidth": 2,
                "Top 10: Output bandwidth": 2,
                "Host information": 1,
                "Filesystems": 4,
            },
            id="linux_dashboard",
        ),
        pytest.param(
            "windows_hosts",
            WindowsHostsDashboard,
            {
                "Host statistics": 0,
                "Service statistics": 0,
                "Total agent execution time": 0,
                "Top 10: Memory utilization": 1,
                "Filesystems": 1,
            },
            id="windows_dashboard",
        ),
    ],
)
def test_host_dashboard(
    dashboard_page: Dashboard,
    dashboard_class: type[LinuxHostsDashboard | WindowsHostsDashboard],
    dashlets_expected_row_count: dict[str, int],
    hosts: str,
    request: pytest.FixtureRequest,
) -> None:
    """Test 'Linux Hosts' and 'Windows Hosts' dashboards.

    Test that when agent data is available, the dashlets on the 'Linux Hosts'
    and 'Windows Hosts' pages have no errors and contain data.
    """
    hosts_count = len(request.getfixturevalue(hosts))
    not_empty_dashboards = dashlets_expected_row_count.keys()
    hosts_dashboard_page = dashboard_class(dashboard_page.page)

    hosts_dashboard_page.check_no_errors()

    # Can be moved down after CMK-18863 is fixed
    logger.info("Check that scatterplots are visible on dashlets")
    for dashlet_title in hosts_dashboard_page.plot_dashlets:
        if dashlet_title in not_empty_dashboards:
            hosts_dashboard_page.wait_for_scatterplot_to_load(dashlet_title)

    logger.info("Check that all expected dashlets are presented on the page")
    for dashlet_title in hosts_dashboard_page.dashlets_list:
        expect(
            hosts_dashboard_page.dashlet(dashlet_title),
            f"Dashlet '{dashlet_title}' is not presented on the page",
        ).to_be_visible()

    logger.info("Check that dashlets with tables are not empty")
    for dashlet_title in hosts_dashboard_page.table_dashlets:
        if dashlet_title in not_empty_dashboards:
            expect(
                hosts_dashboard_page.dashlet_table_rows(dashlet_title),
                f"Table in dashlet '{dashlet_title}' is empty",
            ).to_have_count(dashlets_expected_row_count[dashlet_title] * hosts_count)

    logger.info("Check that dashlets with chart contain data")
    for dashlet_title in hosts_dashboard_page.chart_dashlets:
        if dashlet_title in not_empty_dashboards:
            hosts_dashboard_page.check_hexagon_chart_is_not_empty(dashlet_title)
            assert int(hosts_dashboard_page.total_count(dashlet_title).inner_text()) > 0, (
                f"Total count in dashlet '{dashlet_title}' is 0"
            )


@pytest.mark.parametrize(
    "dashlet_title, expected_service_name, expected_metric",
    [
        pytest.param(
            "Top 10: Memory utilization",
            "Memory",
            "RAM usage",
            id="memory_utilization",
        ),
        pytest.param(
            "Top 10: Disk utilization",
            "Disk IO SUMMARY",
            "Disk utilization",
            id="disk_utilization",
        ),
    ],
)
def test_top_list_dashlets_settings(
    dashlet_title: str,
    expected_service_name: str,
    expected_metric: str,
    dashboard_page: Dashboard,
) -> None:
    """Check settings of 'Top list' dashlets on 'Linux Hosts' dashboard page.

    Check that 'Service (exact match)' and 'Metric' fields contain expected values
    for some of the 'Top list' dashlets.
    """
    hosts_dashboard_page = LinuxHostsDashboard(dashboard_page.page)
    hosts_dashboard_page.enter_layout_mode()
    hosts_dashboard_page.edit_properties_button(dashlet_title).click()
    edit_element_top_list_page = EditElementTopList(dashboard_page.page, navigate_to_page=False)
    expect(
        edit_element_top_list_page.service_exact_match_search_field,
        "Unexpected values in 'Service (exact match)' field",
    ).to_contain_text(re.compile(f"{expected_service_name}$"))
    expect(
        edit_element_top_list_page.metric_search_field,
        "Unexpected values in 'Metric' field",
    ).to_contain_text(re.compile(f"{expected_metric}$"))


def test_dashlet_filters(dashboard_page: Dashboard, linux_hosts: list[str]) -> None:
    """Test that applying filters for 'Top 10: CPU utilization' dashlet works correctly.

    Test that after applying 'Site', 'Host label' and both filters together in dashlet settings,
    the dashlet table contains all expected hosts.
    """
    hosts_count = len(linux_hosts)
    dashlet_title = "Top 10: CPU utilization"
    linux_hosts_dashboard_page = LinuxHostsDashboard(dashboard_page.page)

    logger.info("Apply 'Site' filter for '%s' dashlet", dashlet_title)
    linux_hosts_dashboard_page.enter_layout_mode()
    linux_hosts_dashboard_page.edit_properties_button(dashlet_title).click()
    edit_element_top_list_page = EditElementTopList(dashboard_page.page, navigate_to_page=False)
    edit_element_top_list_page.add_host_filter_site("Local site gui_e2e_central")
    edit_element_top_list_page.save_button.click()
    linux_hosts_dashboard_page.validate_page()

    logger.info("Check that filtered '%s' dashlet contains all expected hosts", dashlet_title)
    expect(linux_hosts_dashboard_page.dashlet_table_rows(dashlet_title)).to_have_count(hosts_count)

    logger.info("Apply 'Label' filter")
    linux_hosts_dashboard_page.edit_properties_button(dashlet_title).click()
    edit_element_top_list_page.add_host_filter_host_labels("cmk/os_family:linux")
    edit_element_top_list_page.save_button.click()
    linux_hosts_dashboard_page.validate_page()

    logger.info("Check that filtered '%s' dashlet contains all expected hosts", dashlet_title)
    expect(linux_hosts_dashboard_page.dashlet_table_rows(dashlet_title)).to_have_count(hosts_count)

    logger.info("Delete 'Site' filter")
    linux_hosts_dashboard_page.edit_properties_button(dashlet_title).click()
    edit_element_top_list_page.remove_host_filter_button("Site").click()
    edit_element_top_list_page.save_button.click()
    linux_hosts_dashboard_page.validate_page()

    logger.info("Check that filtered '%s' dashlet contains all expected hosts", dashlet_title)
    expect(linux_hosts_dashboard_page.dashlet_table_rows(dashlet_title)).to_have_count(hosts_count)

    logger.info("Delete 'label' filter")
    linux_hosts_dashboard_page.edit_properties_button(dashlet_title).click()
    edit_element_top_list_page.remove_host_filter_button("Host labels").click()
    edit_element_top_list_page.save_button.click()


def test_add_top_list_dashlet(dashboard_page: Dashboard, linux_hosts: list[str]) -> None:
    """Test 'Top list' dashlet for 'Total execution time' metric can be added to the dashboard.

    Add 'Top list' dashlet for 'Total execution time' metric to the 'Linux Hosts' dashboard. Check
    that the dashlet is visible and not empty.
    """
    hosts_count = len(linux_hosts)
    metric = "Total execution time"
    linux_hosts_dashboard_page = LinuxHostsDashboard(dashboard_page.page)
    linux_hosts_dashboard_page.enter_layout_mode()

    logger.info("Create 'Top list' dashlet for '%s' metric", metric)
    linux_hosts_dashboard_page.main_area.click_item_in_dropdown_list("Add", "Top list")
    add_element_top_list_page = AddElementTopList(dashboard_page.page, navigate_to_page=False)
    add_element_top_list_page.select_metric(metric)
    add_element_top_list_page.check_show_service_name_checkbox(True)
    add_element_top_list_page.save_button.click()
    linux_hosts_dashboard_page.validate_page()

    logger.info("Check that new dashlet is visible and not empty")
    expect(linux_hosts_dashboard_page.dashlet(f"Top 10: {metric}")).to_be_visible()
    rows_count = linux_hosts_dashboard_page.dashlet_table_rows(f"Top 10: {metric}").count()
    assert rows_count % hosts_count == 0, "Dashlet table has unexpected amount of rows"

    logger.info("Delete 'Top list' dashlet for '%s' metric", metric)
    linux_hosts_dashboard_page.delete_dashlet_button(f"Top 10: {metric}").click()
    linux_hosts_dashboard_page.delete_confirmation_button.click()
