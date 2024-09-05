#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from typing import Type

import pytest
from playwright.sync_api import expect

from tests.testlib.playwright.pom.dashboard import Dashboard
from tests.testlib.playwright.pom.monitor.hosts_dashboard import (
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


@pytest.mark.skip("Due to problems with reading dumps from qa-test-data repo")
@pytest.mark.parametrize(
    "setup_host_using_agent_dump, dashboard_class, dashlets_expected_to_have_data",
    [
        pytest.param(
            "linux-2.4.0-2024.08.27",
            LinuxHostsDashboard,
            [
                "Host statistics",
                "Service statistics",
                "Total agent execution time",
                "Top 10: CPU utilization",
                "Top 10: Memory utilization",
                "Top 10: Input bandwidth",
                "Top 10: Output bandwidth",
                "Host information",
                "Filesystems",
            ],
            id="linux_dashboard",
        ),
        pytest.param(
            "windows-2.3.0p10",
            WindowsHostsDashboard,
            [
                "Host statistics",
                "Service statistics",
                "Total agent execution time",
                "Top 10: Memory utilization",
                "Filesystems",
            ],
            id="windows_dashboard",
        ),
    ],
    indirect=["setup_host_using_agent_dump"],
)
def test_host_dashboard(
    dashboard_page: Dashboard,
    dashboard_class: Type[LinuxHostsDashboard | WindowsHostsDashboard],
    dashlets_expected_to_have_data: list[str],
    setup_host_using_agent_dump: None,
) -> None:
    hosts_dashboard_page = dashboard_class(dashboard_page.page)

    hosts_dashboard_page.check_no_errors(timeout=5000)

    # Can be moved down after CMK-18863 is fixed
    logger.info("Check that scatterplots are visible on dashlets")
    for dashlet_title in hosts_dashboard_page.plot_dashlets:
        if dashlet_title in dashlets_expected_to_have_data:
            hosts_dashboard_page.wait_for_scatterplot_to_load(dashlet_title)

    logger.info("Check that all expected dashlets are presented on the page")
    for dashlet_title in hosts_dashboard_page.dashlets_list:
        expect(
            hosts_dashboard_page.dashlet(dashlet_title),
            f"Dashlet '{dashlet_title}' is not presented on the page",
        ).to_be_visible()

    logger.info("Check that dashlets with tables are not empty")
    for dashlet_title in hosts_dashboard_page.table_dashlets:
        if dashlet_title in dashlets_expected_to_have_data:
            first_row = hosts_dashboard_page.dashlet_table_rows(dashlet_title).nth(0)
            expect(
                first_row,
                f"Table in dashlet '{dashlet_title}' is empty",
            ).to_be_visible()

    logger.info("Check that dashlets with chart contain data")
    for dashlet_title in hosts_dashboard_page.chart_dashlets:
        if dashlet_title in dashlets_expected_to_have_data:
            hosts_dashboard_page.check_hexagon_chart_is_not_empty(dashlet_title)
            assert (
                int(hosts_dashboard_page.total_count(dashlet_title).inner_text()) > 0
            ), f"Total count in dashlet '{dashlet_title}' is 0"
