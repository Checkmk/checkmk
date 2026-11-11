#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Drilling back up from a page a dashboard drill-down opened.

E2E rather than Vitest: the way back is the browser's own history, and the page it returns to
restores its filters from the URL the dashboard wrote there. That a page names the way back is
covered by unit tests of the dashboard and the view page.
"""

import re
from collections.abc import Iterator
from typing import Final

import pytest
from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.pom.monitor.custom_dashboard import CustomDashboard
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.monitor.drilldown_dashboards import (
    apply_host_name_runtime_filter,
    apply_service_name_runtime_filter,
    CPU_SERVICE,
    cpu_top_list,
    inherited_link,
    url_variables,
)
from tests.system.gui.testlib.playwright.pom.monitor.rest_dashboard import (
    open_dashboard,
    rest_dashboard,
)
from tests.system.gui.testlib.playwright.pom.page import CmkPage
from tests.testlib.system.site import Site

_A_ID: Final = "e2e_drill_up_a"
_A_TITLE: Final = "E2E drill-up A"
_B_ID: Final = "e2e_drill_up_b"
_B_TITLE: Final = "E2E drill-up B"
_C_ID: Final = "e2e_drill_up_c"
_C_TITLE: Final = "E2E drill-up C"
_WIDGET_TITLE: Final = "Hosts"


def _dashboard_url(dashboard_id: str) -> re.Pattern[str]:
    return re.compile(rf"dashboard\.py\?name={dashboard_id}(?:&|$)")


def _drill_down(source: CustomDashboard, host_name: str, target_url: re.Pattern[str]) -> None:
    source.click_and_wait_for_navigation(
        source.get_widget_link(_WIDGET_TITLE, host_name), target_url
    )


def _drill_up(
    page: CmkPage, button: Locator, source_title: str, source_url: re.Pattern[str]
) -> None:
    expect(
        button, "The page a drill-down opened does not offer the way back"
    ).to_have_accessible_name(f"Back to {source_title}")
    page.click_and_wait_for_navigation(button, source_url)


def _expect_narrowed_to(dashboard: CustomDashboard, host_name: str) -> None:
    rows = dashboard.get_widget_table_rows(_WIDGET_TITLE)
    expect(rows, f"{dashboard.page_title!r} is not narrowed to one host").to_have_count(1)
    expect(rows, f"{dashboard.page_title!r} lists another host").to_contain_text(host_name)


@pytest.fixture(name="drill_chain")
def fixture_drill_chain(
    dashboard_page: MainDashboard, test_site: Site
) -> Iterator[CustomDashboard]:
    """Dashboard A, opened in the browser, whose top list drills down into B, whose top list
    drills down into C."""
    with (
        rest_dashboard(
            test_site,
            dashboard_id=_C_ID,
            title=_C_TITLE,
            widgets={"hosts": cpu_top_list(_WIDGET_TITLE, {"type": "none"})},
        ),
        rest_dashboard(
            test_site,
            dashboard_id=_B_ID,
            title=_B_TITLE,
            widgets={"hosts": cpu_top_list(_WIDGET_TITLE, inherited_link("dashboards", _C_ID))},
        ),
        rest_dashboard(
            test_site,
            dashboard_id=_A_ID,
            title=_A_TITLE,
            widgets={"hosts": cpu_top_list(_WIDGET_TITLE, inherited_link("dashboards", _B_ID))},
        ),
    ):
        yield open_dashboard(dashboard_page.page, test_site, _A_ID, _A_TITLE)


def test_drill_up_retraces_a_two_step_drill_down(
    linux_hosts: list[str], drill_chain: CustomDashboard
) -> None:
    """Drilling up from A → B → C returns to B with the filters it had at the click, still
    offering the way back to A, and from there to A, narrowed by its own filter again."""
    host = linux_hosts[0]
    host_filter = apply_host_name_runtime_filter(drill_chain, host)
    _expect_narrowed_to(drill_chain, host)
    _drill_down(drill_chain, host, _dashboard_url(_B_ID))
    b = CustomDashboard(drill_chain.page, _B_TITLE, navigate_to_page=False)
    # A filter of B's own, as the drill-down carries no service regex.
    service_filter = apply_service_name_runtime_filter(b, CPU_SERVICE)
    _drill_down(b, host, _dashboard_url(_C_ID))
    c = CustomDashboard(b.page, _C_TITLE, navigate_to_page=False)

    _drill_up(c, c.drill_up_button, _B_TITLE, _dashboard_url(_B_ID))
    b = CustomDashboard(c.page, _B_TITLE, navigate_to_page=False)
    carried = url_variables(b.page.url)
    expected = {"host_regex": host_filter, "host": host, "service_regex": service_filter}
    assert {name: carried.get(name) for name in expected} == expected, (
        f"B does not have the filters it had at the click: {b.page.url}"
    )
    _drill_up(b, b.drill_up_button, _A_TITLE, _dashboard_url(_A_ID))

    a = CustomDashboard(b.page, _A_TITLE, navigate_to_page=False)
    assert url_variables(a.page.url).get("host_regex") == host_filter, (
        f"A lost its runtime filter on the way back: {a.page.url}"
    )
    _expect_narrowed_to(a, host)
    expect(a.drill_up_button, "A offers a way back after returning").to_have_count(0)
