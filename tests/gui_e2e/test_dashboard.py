#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from tests.gui_e2e.testlib.playwright.pom.customize.edit_dashboard import (
    EditDashboards,
    NewDashboardCaracteristics,
)
from tests.gui_e2e.testlib.playwright.pom.monitor.custom_dashboard import CustomDashboard
from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.gui_e2e.testlib.playwright.pom.sidebar.widget_wizard_sidebar import (
    ServiceMetricDropdownOptions,
    VisualizationType,
    WidgetType,
)
from tests.testlib.utils import is_cleanup_enabled


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
