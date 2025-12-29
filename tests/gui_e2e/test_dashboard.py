#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest
from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.pom.customize.edit_dashboard import (
    EditDashboards,
    NewDashboardCaracteristics,
)
from tests.gui_e2e.testlib.playwright.pom.monitor.custom_dashboard import CustomDashboard
from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.gui_e2e.testlib.playwright.pom.monitor.hosts_dashboard import LinuxHostsDashboard
from tests.gui_e2e.testlib.playwright.pom.sidebar.widget_wizard_sidebar import (
    ServiceMetricDropdownOptions,
    VisualizationType,
    WidgetType,
)
from tests.testlib.utils import is_cleanup_enabled


@pytest.fixture(scope="function")
def cloned_linux_hosts_dashboard(
    dashboard_page: MainDashboard,
) -> Iterator[CustomDashboard]:
    """Fixture to clone the 'Linux hosts' dashboard and return the cloned instance."""
    linux_hosts_dashboard = LinuxHostsDashboard(dashboard_page.page)
    linux_hosts_dashboard.clone_dashboard()

    cloned_linux_hosts_dashboard = CustomDashboard(
        linux_hosts_dashboard.page, linux_hosts_dashboard.page_title, navigate_to_page=False
    )

    yield cloned_linux_hosts_dashboard
    # Cleanup: delete the cloned dashboard after the test
    if is_cleanup_enabled():
        edit_dashboards = EditDashboards(dashboard_page.page)
        edit_dashboards.delete_dashboard(cloned_linux_hosts_dashboard.page_title)


def test_create_new_dashboard(dashboard_page: MainDashboard, linux_hosts: list[str]) -> None:
    """Test dashboard creation from scratch.

    Steps:
        1. Navigate to the dashboard page.
        2. Create a new dashboard.
        3. Add a "CPU utilization" top list widget to the dashboard.
        4. Check that the widget is present on the dashboard.
        5. Check the hosts are present in the widget.
        6. Delete the created dashboard.
    """

    edit_dashboards = EditDashboards(dashboard_page.page)
    custom_dashboard: CustomDashboard = edit_dashboards.create_new_dashboard(
        NewDashboardCaracteristics(name="Test Dashboard")
    )

    widget_metric = "CPU utilization"
    widget_title = f"Top 10: {widget_metric}"

    try:
        widget_wizard = custom_dashboard.open_add_widget_sidebar(WidgetType.METRICS_AND_GRAPHS)
        widget_wizard.select_service_metric(ServiceMetricDropdownOptions(widget_metric))
        widget_wizard.select_visualization_type(VisualizationType.TOP_LIST)
        widget_wizard.add_and_place_widget_button.click()
        custom_dashboard.save_button.click()

        custom_dashboard = CustomDashboard(
            custom_dashboard.page, custom_dashboard.page_title, navigate_to_page=False
        )
        custom_dashboard.check_widget_is_present(widget_title)

        for host_name in custom_dashboard.get_widget_table_column_cells(
            widget_title, column_index=1
        ).all():
            assert host_name.text_content() in linux_hosts, (
                f"Unexpected host name found in widget '{widget_title}': "
                f"{host_name.text_content()}. Only one of "
                f"{', '.join(linux_hosts)} hosts is expected"
            )

    finally:
        if is_cleanup_enabled():
            edit_dashboards.navigate()
            edit_dashboards.delete_dashboard(custom_dashboard.page_title)


@pytest.mark.parametrize(
    "widget_title, expected_service_name, expected_metric",
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
def test_top_list_widgets_settings(
    linux_hosts: list[str],
    widget_title: str,
    expected_service_name: str,
    expected_metric: str,
    cloned_linux_hosts_dashboard: CustomDashboard,
) -> None:
    """Check settings of 'Top list' widgets on 'Linux Hosts' dashboard page.

    Check that 'Service (exact match)' and 'Metric' fields contain expected values
    for some of the 'Top list' widgets.

    Steps:
        1. Navigate to the 'Linux Hosts' dashboard page.
        2. Clone the built-in dashboard.
        3. Enter "edit widgets" mode.
        4. Open settings of the 'Top 10: Memory utilization' or 'Top 10: Disk utilization' widget
           properties.
        5. Check that 'Service (exact match)' filter contains expected service name.
        6. Check that 'Service metric' field contains expected metric name.
    """
    cloned_linux_hosts_dashboard.enter_edit_widgets_mode()
    widget_wizard = cloned_linux_hosts_dashboard.open_edit_widget_sidebar(
        WidgetType.METRICS_AND_GRAPHS, widget_title
    )

    expect(
        service_filter_combobox := widget_wizard.get_service_filter_combobox(
            "Service (exact match)"
        ),
        message=(
            f"Unexpected value in 'Service (exact match)' filter combobox."
            f" Expected '{expected_service_name}'"
            f"; actual text is '{service_filter_combobox.text_content()}"
        ),
    ).to_have_text(expected_service_name)

    expect(
        widget_wizard.service_metric_combobox,
        message=(
            f"Unexpected value in 'Service metric' combobox. Expected '{expected_metric}'"
            f"; actual text is '{widget_wizard.service_metric_combobox.text_content()}'"
        ),
    ).to_have_text(expected_metric)
