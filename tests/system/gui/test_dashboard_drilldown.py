#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Drilling down from a dashboard widget with an inherited link.

E2E rather than Vitest: the filters a click carries reach a page the backend renders from the
URL, and only there narrow the target's widget. Only a browser shows a Views widget's column
link leaving the iframe the view renders in. The link setting, the links of each widget and
what a custom link carries are covered by Vitest and unit tests.
"""

import re
from collections.abc import Iterator
from typing import Final

import pytest
from playwright.sync_api import expect

from tests.system.gui.testlib.api_helpers import (
    core_checks_paused,
    create_and_delete_hosts,
    LOCALHOST_IPV4,
)
from tests.system.gui.testlib.host_details import HostDetails
from tests.system.gui.testlib.playwright.pom.monitor.custom_dashboard import CustomDashboard
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import (
    MainDashboard,
    ProblemDashboard,
)
from tests.system.gui.testlib.playwright.pom.monitor.drilldown_dashboards import (
    apply_host_name_runtime_filter,
    cpu_top_list,
    inherited_link,
    url_variables,
)
from tests.system.gui.testlib.playwright.pom.monitor.rest_dashboard import (
    open_dashboard,
    rest_dashboard,
)
from tests.testlib.system.site import Site

_SOURCE_DASHBOARD_ID: Final = "e2e_drilldown_source_dashboard"
_SOURCE_DASHBOARD_TITLE: Final = "E2E drill-down source dashboard"
_SOURCE_WIDGET_TITLE: Final = "Source hosts"
_TARGET_DASHBOARD_ID: Final = "e2e_drilldown_target_dashboard"
_TARGET_DASHBOARD_TITLE: Final = "E2E drill-down target dashboard"
_TARGET_WIDGET_TITLE: Final = "Target hosts"

_DOWN_HOST: Final = "e2e-drilldown-down-host"
_HOST_DOWN: Final = 1
# The Views widget of the built-in problem dashboard whose host column links to the host's view.
_HOST_PROBLEMS_WIDGET_TITLE: Final = "Host problems (unhandled)"
_HOST_VIEW_URL: Final = re.compile(r"view\.py\?.*view_name=host(?:&|$)")

_LINUX_LABEL: Final = "cmk/os_family:linux"
# The URL variable a host label filter of a single label carries the label in.
_LABEL_VARIABLE: Final = "host_labels_1_vs_1_vs"


def _host_label_filter(label: str) -> dict[str, str]:
    """The variables of a host label filter matching the single label."""
    return {
        "host_labels_count": "1",
        "host_labels_1_bool": "and",
        "host_labels_indexof_1": "1",
        "host_labels_1_vs_count": "1",
        "host_labels_1_vs_1_bool": "and",
        _LABEL_VARIABLE: label,
        "host_labels_1_vs_indexof_1": "1",
    }


@pytest.fixture(name="inherited_link_dashboards")
def fixture_inherited_link_dashboards(
    dashboard_page: MainDashboard, test_site: Site
) -> Iterator[CustomDashboard]:
    """A source dashboard, opened in the browser, whose top list links its hosts to a target
    dashboard listing hosts too.

    The source filters its widgets by site, and the top list by a host label.
    """
    with (
        rest_dashboard(
            test_site,
            dashboard_id=_TARGET_DASHBOARD_ID,
            title=_TARGET_DASHBOARD_TITLE,
            widgets={"hosts": cpu_top_list(_TARGET_WIDGET_TITLE, {"type": "none"})},
        ),
        rest_dashboard(
            test_site,
            dashboard_id=_SOURCE_DASHBOARD_ID,
            title=_SOURCE_DASHBOARD_TITLE,
            widgets={
                "hosts": cpu_top_list(
                    _SOURCE_WIDGET_TITLE,
                    inherited_link("dashboards", _TARGET_DASHBOARD_ID),
                    filters={"host_labels": _host_label_filter(_LINUX_LABEL)},
                )
            },
            filters={"siteopt": {"site": test_site.id}},
        ),
    ):
        yield open_dashboard(
            dashboard_page.page, test_site, _SOURCE_DASHBOARD_ID, _SOURCE_DASHBOARD_TITLE
        )


def test_inherited_link_carries_dashboard_widget_runtime_filters_and_clicked_host(
    test_site: Site,
    linux_hosts: list[str],
    inherited_link_dashboards: CustomDashboard,
) -> None:
    """A click on a host of a top list with an inherited link opens the target with the
    dashboard's, the widget's and the runtime filters, and the clicked host."""
    source = inherited_link_dashboards
    clicked = linux_hosts[0]
    host_filter = apply_host_name_runtime_filter(source, clicked)
    expect(
        source.get_widget_table_rows(_SOURCE_WIDGET_TITLE),
        "The source top list does not narrow to the runtime filter",
    ).to_have_count(1)

    source.click_and_wait_for_navigation(
        source.get_widget_link(_SOURCE_WIDGET_TITLE, clicked),
        re.compile(rf"dashboard\.py\?name={_TARGET_DASHBOARD_ID}(?:&|$)"),
    )

    target = CustomDashboard(source.page, _TARGET_DASHBOARD_TITLE, navigate_to_page=False)
    carried = url_variables(target.page.url)
    expected = {
        "site": test_site.id,
        _LABEL_VARIABLE: _LINUX_LABEL,
        "host_regex": host_filter,
        "host": clicked,
    }
    assert {name: carried.get(name) for name in expected} == expected, (
        f"The target did not receive every filter: {target.page.url}"
    )
    rows = target.get_widget_table_rows(_TARGET_WIDGET_TITLE)
    expect(rows, "The target does not narrow to the clicked host").to_have_count(1)
    expect(rows, "The target lists another host than the clicked one").to_contain_text(clicked)


@pytest.fixture(name="down_host")
def fixture_down_host(test_site: Site) -> Iterator[str]:
    """A host of its own in the down state, so the problem dashboard lists it."""
    host = HostDetails(name=_DOWN_HOST, site=test_site.id, ip=LOCALHOST_IPV4)
    with create_and_delete_hosts([host], test_site), core_checks_paused(test_site):
        test_site.send_host_check_result(_DOWN_HOST, _HOST_DOWN, "FAKE DOWN for the drill-down")
        yield _DOWN_HOST


def test_a_views_widget_column_link_opens_its_target_in_the_whole_page(
    dashboard_page: MainDashboard, down_host: str
) -> None:
    """A click on a host of a Views widget's column link opens the host's view in the whole
    page, not inside the widget's iframe."""
    problems = ProblemDashboard(dashboard_page.page)

    problems.click_and_wait_for_navigation(
        problems.get_widget_link(_HOST_PROBLEMS_WIDGET_TITLE, down_host, iframed=True),
        _HOST_VIEW_URL,
    )

    expect(problems.page, "The link opened its target inside the widget's iframe").to_have_url(
        _HOST_VIEW_URL
    )
    assert url_variables(problems.page.url).get("host") == down_host, (
        f"The target did not receive the clicked host: {problems.page.url}"
    )
