#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""A statistics widget's link whose filter takes the values of all hosts of the clicked part.

The link leads to a page that values the filter on the click and redirects to the target. E2E
rather than a unit test: the address the widget builds meets the page that reads it, and in a
new tab the way back follows the referrer the redirect keeps. What the page values and where it
redirects is covered by unit tests.
"""

import re
from collections.abc import Iterator
from typing import Final

import pytest
from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.pom.monitor.all_hosts import AllHosts
from tests.system.gui.testlib.playwright.pom.monitor.custom_dashboard import CustomDashboard
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.monitor.drilldown_dashboards import (
    custom_link,
    host_stats,
    url_variables,
)
from tests.system.gui.testlib.playwright.pom.monitor.rest_dashboard import (
    open_dashboard,
    rest_dashboard,
)
from tests.testlib.system.site import Site

_DASHBOARD_ID: Final = "e2e_stats_link_dashboard"
_DASHBOARD_TITLE: Final = "E2E statistics link"
_WIDGET_TITLE: Final = "Host statistics"

_STATS_LINK_PAGE: Final = re.compile(r"^dashboard_stats_link\.py\?")
_DASHBOARD_URL: Final = re.compile(rf"dashboard\.py\?name={_DASHBOARD_ID}(?:&|$)")
# The page names the target last, after the filters.
_ALL_HOSTS_URL: Final = re.compile(r"view\.py\?(?:.*&)?view_name=allhosts(?:&|$)")


@pytest.fixture(name="stats_dashboard")
def fixture_stats_dashboard(
    dashboard_page: MainDashboard, test_site: Site
) -> Iterator[CustomDashboard]:
    """A dashboard, opened in the browser, whose host statistics link each part to 'All hosts',
    carrying the sites of the part's hosts."""
    link = custom_link("All hosts", "views", "allhosts", [{"filter_id": "sites"}])
    with rest_dashboard(
        test_site,
        dashboard_id=_DASHBOARD_ID,
        title=_DASHBOARD_TITLE,
        widgets={"stats": host_stats(_WIDGET_TITLE, link)},
    ):
        yield open_dashboard(dashboard_page.page, test_site, _DASHBOARD_ID, _DASHBOARD_TITLE)


def _total_link(dashboard: CustomDashboard) -> Locator:
    """The link of the total, which stands for all hosts."""
    link = dashboard.get_widget(_WIDGET_TITLE).get_by_role("link", name=re.compile(r"Total$"))
    expect(link, "The total does not lead to the page that values its filter").to_have_attribute(
        "href", _STATS_LINK_PAGE
    )
    return link


def _expect_all_hosts_of_the_site(view: AllHosts, test_site: Site, host_name: str) -> None:
    assert url_variables(view.page.url).get("sites") == test_site.id, (
        f"The target lacks the sites of the clicked part's hosts: {view.page.url}"
    )
    view.check_host_is_present(host_name)


def test_a_statistics_link_opened_in_a_new_tab_leads_back_to_the_dashboard(
    test_site: Site, linux_hosts: list[str], stats_dashboard: CustomDashboard
) -> None:
    """A new tab has no history, so the way back follows the referrer, which the redirect
    keeps as the dashboard."""
    link = _total_link(stats_dashboard)

    with stats_dashboard.page.context.expect_page() as new_tab_info:
        link.click(modifiers=["ControlOrMeta"])
    new_tab = new_tab_info.value
    try:
        new_tab.wait_for_url(_ALL_HOSTS_URL, wait_until="load")
        view = AllHosts(new_tab, navigate_to_page=False)
        _expect_all_hosts_of_the_site(view, test_site, linux_hosts[0])

        view.click_and_wait_for_navigation(view.drill_up_button, _DASHBOARD_URL)

        CustomDashboard(new_tab, _DASHBOARD_TITLE, navigate_to_page=False)
    finally:
        new_tab.close()
