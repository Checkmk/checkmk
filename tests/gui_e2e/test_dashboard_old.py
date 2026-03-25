#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: File deprecated -> to remove when dashboard tests migration is competed

import logging
import re
from collections.abc import Iterator

import pytest
from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.pom.customize.dashboard_properties_old import (
    CreateDashboard,
    EditDashboard,
)
from tests.gui_e2e.testlib.playwright.pom.monitor.custom_dashboard_old import CustomDashboard
from tests.gui_e2e.testlib.playwright.pom.monitor.dashboard_old import (
    MainDashboard,
    SummaryDashletType,
)
from tests.gui_e2e.testlib.playwright.pom.monitor.hosts_dashboard_old import (
    LinuxHostsDashboard,
)
from tests.gui_e2e.testlib.playwright.pom.tactical_overview_snapin import TacticalOverviewSnapin
from tests.testlib.site import Site
from tests.testlib.utils import is_cleanup_enabled

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.skip(reason="[PEV] CMK-25981: Migration to the new dashboard already done")


@pytest.fixture(scope="function")
def cloned_linux_hosts_dashboard(
    dashboard_page: MainDashboard,
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
    if is_cleanup_enabled():
        cloned_linux_hosts_dashboard.delete()


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


@pytest.mark.skip(reason="CMK-26831: UI got stuck on adding 'Host state summary' dashlet")
@pytest.mark.parametrize(
    "bulk_create_hosts_remote_site, dashlet_to_add, dashlet_title",
    [
        pytest.param(
            (3, True),
            SummaryDashletType.HOST,
            "Hosts : UP",
            id="host_state_summary_dashlet",
        ),
        pytest.param(
            (3, True),
            SummaryDashletType.SERVICE,
            "Services : OK",
            id="service_state_summary_dashlet",
        ),
    ],
    indirect=["bulk_create_hosts_remote_site"],
)
def test_builtin_dashboard_filter_by_site(
    dashboard_page: MainDashboard,
    test_site: Site,
    remote_site_wato_disabled: Site,
    bulk_create_hosts_remote_site: list[dict[str, object]],
    dashlet_to_add: SummaryDashletType,
    dashlet_title: str,
    windows_hosts: list[str],
    linux_hosts: list[str],
) -> None:
    """
    Test filtering of 'Host state summary' and 'Service state summary' dashlets by site.

    The fixtures 'windows_hosts' and 'linux_hosts' are mentioned in parameters to ease
    understanding of how hosts and services are created on the central site.

    Steps:
        1. Creating hosts on remote site via bulk_create_hosts_remote_site fixture.
        2. Waiting for data replication between central and remote sites to be in sync.
        3. Adding a single parametrized dashlet, either 'Host state summary' or
           'Service state summary'.
        4. Applying site-specific filters.
        5. Verifying that only data from the selected site is displayed.
    """
    dashboard_page.page.reload()
    # Wait for tactical overview snapin to show hosts and services, ensuring data replication
    # between sites is synced before making API assertions below.
    overview_snapin = TacticalOverviewSnapin(
        dashboard_page.sidebar.locator("#snapin_container_tactical_overview")
    )
    overview_snapin.hosts_number.wait_for(state="visible")
    overview_snapin.services_number.wait_for(state="visible")
    non_zero_number = re.compile(r"^[1-9]\d*$")
    expect(overview_snapin.hosts_number, "Overview snapin shows zero number of hosts").to_have_text(
        non_zero_number
    )
    expect(
        overview_snapin.services_number, "Overview snapin shows zero number of services"
    ).to_have_text(non_zero_number)

    # Get number of hosts and services on central site via openapi call. Those numbers also include
    # hosts and services created on remote_site.
    exp_central_hosts_count, exp_central_services_count = test_site.get_host_and_service_count()
    # Get number of hosts and services on remote site created by the fixture.
    exp_remote_hosts_count = exp_remote_services_count = len(bulk_create_hosts_remote_site)

    # Adjust expected service count on central site
    exp_central_hosts_count -= exp_remote_hosts_count
    exp_central_services_count -= exp_remote_services_count
    logger.info(
        "Expecting %d hosts and %d services on central site",
        exp_central_hosts_count,
        exp_central_services_count,
    )
    logger.info(
        "Expecting %d hosts and %d services on remote site",
        exp_remote_hosts_count,
        exp_remote_services_count,
    )

    create_dashboard = CreateDashboard(dashboard_page.page)
    custom_dashboard = create_dashboard.create_custom_dashboard(dashlet_to_add)

    try:
        custom_dashboard.add_dashlet(dashlet_to_add)
        custom_dashboard.leave_layout_mode()

        custom_dashboard.check_dashlet_is_present(dashlet_title)

        logger.info("Without site filter")
        custom_dashboard.verify_summary_dashlet_shows_site_related_data(
            dashlet_title,
            exp_central_hosts_count + exp_remote_hosts_count
            if dashlet_to_add == SummaryDashletType.HOST
            else exp_central_services_count + exp_remote_services_count,
            "No filter: central and remote sites combined",
        )

        logger.info("Filter by remote site")
        custom_dashboard.apply_filter_to_the_dashboard(
            "Site", f"Remote site {remote_site_wato_disabled.id}", exact=True
        )
        custom_dashboard.leave_layout_mode()
        custom_dashboard.verify_summary_dashlet_shows_site_related_data(
            dashlet_title,
            exp_remote_hosts_count
            if dashlet_to_add == SummaryDashletType.HOST
            else exp_remote_services_count,
            f"Filter: remote site {remote_site_wato_disabled.id} only",
        )

        logger.info("Filter by central site")
        custom_dashboard.apply_filter_to_the_dashboard(
            "Site", f"Local site {test_site.id}", exact=True
        )
        custom_dashboard.leave_layout_mode()
        custom_dashboard.verify_summary_dashlet_shows_site_related_data(
            dashlet_title,
            exp_central_hosts_count
            if dashlet_to_add == SummaryDashletType.HOST
            else exp_central_services_count,
            f"Filter: central site {test_site.id} only",
        )

    finally:
        custom_dashboard.delete()
