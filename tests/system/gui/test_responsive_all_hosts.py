#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Responsiveness E2E sanity check for the experimental Vue "All hosts" view.

Drives the `cmk-monitoring-all-hosts` Vue app (page `monitor_all_hosts.py`,
"All hosts") at the narrowest canonical breakpoint (XS=280) in a real browser
and asserts the browser-only responsive contract: the controls above the table
stay visible and usable when the viewport leaves them almost no room.

This is the regression guard for CMK-35987, where the filter controls above the
table silently disappeared as the window narrowed -- a layout failure only a
real browser at a real width can reproduce.

The sweep is deliberately XS-only: the breakpoint scale itself is pinned at unit
level, and re-driving a real browser plus a site at five widths adds runtime
without proportional value.
"""

import logging
from collections.abc import Iterator

import pytest
from playwright.sync_api import expect

from tests.system.gui.testlib.api_helpers import create_and_delete_hosts, LOCALHOST_IPV4
from tests.system.gui.testlib.host_details import HostDetails
from tests.system.gui.testlib.playwright.pom.monitor.all_hosts_experimental import (
    AllHostsExperimental,
)
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.responsive_helpers import Breakpoint, CANONICAL_BREAKPOINTS
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

RESPONSIVE_HOST = "e2e-responsive-host"

# The one quick filter the page offers; it is the control CMK-35987 dropped.
UNHANDLED_HOST_PROBLEMS = "Unhandled host problems"

# The narrowest canonical breakpoint is where the table overflows and the
# toolbar has to give way to something -- or wrongly to nothing.
NARROWEST: Breakpoint = next(bp for bp in CANONICAL_BREAKPOINTS if bp.name == "XS")


@pytest.fixture(name="responsive_host")
def fixture_responsive_host(test_site: Site) -> Iterator[str]:
    """One host to search for, so "usable" means a search that comes back narrowed."""
    host = HostDetails(name=RESPONSIVE_HOST, site=test_site.id, ip=LOCALHOST_IPV4)
    with create_and_delete_hosts([host], test_site):
        yield RESPONSIVE_HOST


@pytest.fixture(name="narrow_viewport")
def fixture_narrow_viewport(dashboard_page: MainDashboard) -> Iterator[None]:
    """Run the test at the narrowest breakpoint, then hand the page back as found.

    The viewport is a property of the session-wide browser context and the page
    is reused by the tests that follow, so a test that narrows it has to widen it
    again -- on the way out of a failure too, hence a fixture rather than a line
    at the end of the test.
    """
    original = dashboard_page.page.viewport_size
    dashboard_page.page.set_viewport_size(NARROWEST.viewport)
    yield
    if original is not None:
        dashboard_page.page.set_viewport_size(original)


@pytest.mark.usefixtures("narrow_viewport")
def test_the_controls_above_the_table_stay_usable_at_the_narrowest_width(
    dashboard_page: MainDashboard, responsive_host: str
) -> None:
    """Search, quick filter and column picker survive the narrowest supported width.

    "Usable" is asserted, not just "present": a control pushed off-screen or
    covered still answers `to_be_visible` in some layouts, so the search runs a
    round trip and the picker is actually opened.
    """
    all_hosts = AllHostsExperimental(dashboard_page.page)

    expect(all_hosts.search_field).to_be_visible()
    expect(all_hosts.quick_filter(UNHANDLED_HOST_PROBLEMS)).to_be_visible()
    expect(all_hosts.column_picker_trigger).to_be_visible()

    all_hosts.search(responsive_host)
    expect(all_hosts.rows()).to_have_count(1)

    all_hosts.column_picker_trigger.click()
    expect(all_hosts.column_picker_panel).to_be_visible()
