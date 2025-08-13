#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
import re
from collections.abc import Iterator

import pytest
from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.pom.custom_dashboard import CustomDashboard
from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.edit_dashboard import EditDashboard
from tests.gui_e2e.testlib.playwright.pom.monitor.edit_element_top_list import (
    AddElementTopList,
    EditElementTopList,
)
from tests.gui_e2e.testlib.playwright.pom.monitor.hosts_dashboard import (
    LinuxHostsDashboard,
    WindowsHostsDashboard,
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def cloned_linux_hosts_dashboard(
    dashboard_page: Dashboard,
) -> Iterator[CustomDashboard]:
    """Fixture to clone the 'Linux hosts' dashboard and return the cloned instance."""
    linux_hosts_dashboard = LinuxHostsDashboard(dashboard_page.page)
    linux_hosts_dashboard.clone_built_in_dashboard()
    cloned_linux_hosts_dashboard = CustomDashboard(
        linux_hosts_dashboard.page, linux_hosts_dashboard.page_title, navigate_to_page=False
    )
    cloned_linux_hosts_dashboard.leave_layout_mode()
    yield cloned_linux_hosts_dashboard
    # Cleanup: delete the cloned dashboard after the test
    if os.getenv("CLEANUP", "1") == "1":
        cloned_linux_hosts_dashboard.delete()


def test_dashboard_sanity_check(dashboard_page: Dashboard) -> None:
    """Sanity check for the dashboard page.

    Check that all default dashlets, dropdown buttons and icons are visible on the dashboard page.

    Steps:
        1. Navigate to the 'Main dashboard' page.
        2. Check that the page title is correct.
        3. Check that all default dashlets are visible.
        4. Check that all dropdown buttons are visible.
        5. Check that all icons are visible.
        6. Check that the SVGs for 'Host statistics' and 'Service statistics' dashlets are visible.
    """
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

    Steps:
        1. Navigate to the 'Linux Hosts' or 'Windows Hosts' dashboard page.
        2. Check that there are no errors on the page.
        3. Check that scatterplots are visible on dashlets.
        4. Check that all expected dashlets are presented on the page.
        5. Check that dashlets with tables are not empty.
        6. Check that dashlets with charts contain data.
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
    cloned_linux_hosts_dashboard: CustomDashboard,
) -> None:
    """Check settings of 'Top list' dashlets on 'Linux Hosts' dashboard page.

    Check that 'Service (exact match)' and 'Metric' fields contain expected values
    for some of the 'Top list' dashlets.

    Steps:
        1. Navigate to the 'Linux Hosts' dashboard page.
        2. Clone the built-in dashboard.
        3. Enter layout mode.
        4. Open settings of the 'Top 10: Memory utilization' or 'Top 10: Disk utilization' dashlet.
        5. Check that 'Service (exact match)' field contains expected service name.
        6. Check that 'Metric' field contains expected metric name.
    """
    cloned_linux_hosts_dashboard.enter_layout_mode()
    cloned_linux_hosts_dashboard.edit_dashlet_properties_button(dashlet_title).click()
    edit_element_top_list_page = EditElementTopList(
        cloned_linux_hosts_dashboard.page, navigate_to_page=False
    )
    expect(
        edit_element_top_list_page.service_exact_match_search_field,
        "Unexpected values in 'Service (exact match)' field",
    ).to_contain_text(re.compile(f"{expected_service_name}$"))
    expect(
        edit_element_top_list_page.metric_search_field,
        "Unexpected values in 'Metric' field",
    ).to_contain_text(re.compile(f"{expected_metric}$"))


def test_dashlet_filters(
    linux_hosts: list[str], cloned_linux_hosts_dashboard: CustomDashboard
) -> None:
    """Test that applying filters for 'Top 10: CPU utilization' dashlet works correctly.

    Test that after applying 'Site', 'Host label' and both filters together in dashlet settings,
    the dashlet table contains all expected hosts.

    Steps:
        1. Navigate to the 'Linux Hosts' dashboard page.
        2. Clone the built-in dashboard.
        3. Enter layout mode.
        4. Apply 'Site' filter for 'Top 10: CPU utilization' dashlet.
        5. Check that dashlet contains all expected hosts.
        6. Apply 'label' filter for 'Top 10: CPU utilization'
        7. Check that dashlet contains all expected hosts.
        8. Delete 'Site' filter.
        9. Check that dashlet contains all expected hosts.
        10. Delete 'Label' filter.
    """
    hosts_count = len(linux_hosts)
    dashlet_title = "Top 10: CPU utilization"

    logger.info("Apply 'Site' filter for '%s' dashlet", dashlet_title)
    cloned_linux_hosts_dashboard.enter_layout_mode()
    cloned_linux_hosts_dashboard.edit_dashlet_properties_button(dashlet_title).click()
    edit_element_top_list_page = EditElementTopList(
        cloned_linux_hosts_dashboard.page, navigate_to_page=False
    )
    edit_element_top_list_page.add_host_filter_site("Local site gui_e2e_central")
    edit_element_top_list_page.save_button.click()
    cloned_linux_hosts_dashboard.validate_page()

    logger.info("Check that filtered '%s' dashlet contains all expected hosts", dashlet_title)
    expect(cloned_linux_hosts_dashboard.dashlet_table_rows(dashlet_title)).to_have_count(
        hosts_count
    )

    logger.info("Apply 'Label' filter")
    cloned_linux_hosts_dashboard.edit_dashlet_properties_button(dashlet_title).click()
    edit_element_top_list_page.add_host_filter_host_labels("cmk/os_family:linux")
    edit_element_top_list_page.save_button.click()
    cloned_linux_hosts_dashboard.validate_page()

    logger.info("Check that filtered '%s' dashlet contains all expected hosts", dashlet_title)
    expect(cloned_linux_hosts_dashboard.dashlet_table_rows(dashlet_title)).to_have_count(
        hosts_count
    )

    logger.info("Delete 'Site' filter")
    cloned_linux_hosts_dashboard.edit_dashlet_properties_button(dashlet_title).click()
    edit_element_top_list_page.remove_host_filter_button("Site").click()
    edit_element_top_list_page.save_button.click()
    cloned_linux_hosts_dashboard.validate_page()

    logger.info("Check that filtered '%s' dashlet contains all expected hosts", dashlet_title)
    expect(cloned_linux_hosts_dashboard.dashlet_table_rows(dashlet_title)).to_have_count(
        hosts_count
    )

    logger.info("Delete 'Label' filter")
    cloned_linux_hosts_dashboard.edit_dashlet_properties_button(dashlet_title).click()
    edit_element_top_list_page.remove_host_filter_button("Host labels").click()
    edit_element_top_list_page.save_button.click()


def test_add_top_list_dashlet(
    linux_hosts: list[str], cloned_linux_hosts_dashboard: CustomDashboard
) -> None:
    """Test 'Top list' dashlet for 'Total execution time' metric can be added to the dashboard.

    Add 'Top list' dashlet for 'Total execution time' metric to the 'Linux Hosts' dashboard. Check
    that the dashlet is visible and not empty.

    Steps:
        1. Navigate to the 'Linux Hosts' dashboard page.
        2. Clone the built-in dashboard.
        3. Enter layout mode.
        4. Add 'Top list' dashlet for 'Total execution time' metric.
        5. Check that the dashlet is visible and not empty.
        6. Delete the dashlet.
    """
    hosts_count = len(linux_hosts)
    metric = "Total execution time"
    cloned_linux_hosts_dashboard.enter_layout_mode()

    logger.info("Create 'Top list' dashlet for '%s' metric", metric)
    cloned_linux_hosts_dashboard.main_area.click_item_in_dropdown_list("Add", "Top list")
    add_element_top_list_page = AddElementTopList(
        cloned_linux_hosts_dashboard.page, navigate_to_page=False
    )
    add_element_top_list_page.select_metric(metric)
    add_element_top_list_page.check_show_service_name_checkbox(True)
    add_element_top_list_page.save_button.click()
    cloned_linux_hosts_dashboard.validate_page()

    logger.info("Check that new dashlet is visible and not empty")
    expect(cloned_linux_hosts_dashboard.dashlet(f"Top 10: {metric}")).to_be_visible()
    rows_count = cloned_linux_hosts_dashboard.dashlet_table_rows(f"Top 10: {metric}").count()
    assert rows_count % hosts_count == 0, "Dashlet table has unexpected amount of rows"

    logger.info("Delete 'Top list' dashlet for '%s' metric", metric)
    cloned_linux_hosts_dashboard.delete_dashlet_button(f"Top 10: {metric}").click()
    cloned_linux_hosts_dashboard.delete_confirmation_button.click()
    expect(
        cloned_linux_hosts_dashboard.dashlet(f"Top 10: {metric}"),
        message=f"Dashlet 'Top 10: {metric}' is still present after deletion",
    ).not_to_be_attached()


def test_dashboard_required_context_filter_by_host_name(
    linux_hosts: list[str], cloned_linux_hosts_dashboard: CustomDashboard
) -> None:
    """Test filtering of 'Linux Hosts' dashboard by host name.

    Steps:
        1. Navigate to the 'Linux Hosts' dashboard page.
        2. Clone the built-in dashboard.
        3. Edit the dashboard and add 'Host: Host name (regex)' required context filter.
        4. Check that all dashlets contain a warning message about missing context information.
        5. Apply the filter for the first host in the list.
        6. Check that only the first host is visible in the dashlets:
           - 'Top 10: CPU utilization',
           - 'Top 10: Memory utilization',
           - 'Top 10: Input bandwidth'
           - 'Top 10: Output bandwidth'
        7. Apply the filter with non-existing host name.
        8. Check that no hosts are visible in the same dashlets.
    """
    filter_name = "Host name (regex)"
    dashlets_to_check = (
        "Top 10: CPU utilization",
        "Top 10: Memory utilization",
        "Top 10: Input bandwidth",
        "Top 10: Output bandwidth",
    )
    first_host = linux_hosts[0]
    number_of_dashlets = 10
    expected_message = (
        "Unable to render this element, because we miss some required context information "
        "(hostregex). Please update the form on the right to make this element render."
    )

    cloned_linux_hosts_dashboard.check_number_of_dashlets(number_of_dashlets)

    edit_dashboard_page = EditDashboard(cloned_linux_hosts_dashboard)
    edit_dashboard_page.expand_section("Dashboard properties")
    edit_dashboard_page.select_required_context_filter(f"Host: {filter_name}")
    edit_dashboard_page.save_and_go_to_dashboard()

    cloned_linux_hosts_dashboard.check_number_of_dashlets(number_of_dashlets)

    for dashlet in cloned_linux_hosts_dashboard.dashlets.all():
        warning_message = dashlet.locator("div.warning")
        expect(
            warning_message,
            message="Expected Dashlet to contain a warning message when filters aren't applied.",
        ).to_be_visible()

        expect(
            warning_message,
            message=(
                f"Dashlet does not contain the expected warning message ('{expected_message}'). "
                f"Actual message: {warning_message.text_content()}"
            ),
        ).to_have_text(expected_message)

    cloned_linux_hosts_dashboard.apply_filter_to_the_dashboard(
        filter_name, first_host, open_filters_popup=False
    )
    cloned_linux_hosts_dashboard.check_number_of_dashlets(number_of_dashlets)

    for dashlet_title in dashlets_to_check:
        for host_name in cloned_linux_hosts_dashboard.dashlet_table_column_cells(
            dashlet_title, column_index=1
        ).all():
            assert host_name.text_content() == first_host, (
                f"Unexpected host name found in dashlet '{dashlet_title}': "
                f"{host_name.text_content()}. Only '{first_host}' host is expected"
            )

    cloned_linux_hosts_dashboard.apply_filter_to_the_dashboard(filter_name, "xXxXxXx")
    cloned_linux_hosts_dashboard.check_number_of_dashlets(number_of_dashlets)

    for dashlet_title in dashlets_to_check:
        expect(
            cloned_linux_hosts_dashboard.dashlet(dashlet_title).locator("div.simplebar-content"),
            message=f"Dashlet '{dashlet_title}' is not empty.",
        ).to_have_text("No entries.")
