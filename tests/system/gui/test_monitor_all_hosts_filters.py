#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Browser flow for the column filters of the experimental "All hosts" page.

Filtering is applied server-side, so what only a browser proves is the whole
round trip: opening a column's funnel, committing a choice, and the table coming
back narrowed -- then widening again when the choice is withdrawn.

The state filtered on is read off the table rather than assumed, because which
state a fixture host reaches depends on a check cycle. Taking the state the page
itself reports keeps the assertion deterministic without waiting for one.
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
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

FILTER_HOST = "e2e-filter-host"


@pytest.fixture(name="filter_host")
def fixture_filter_host(test_site: Site) -> Iterator[str]:
    host = HostDetails(name=FILTER_HOST, site=test_site.id, ip=LOCALHOST_IPV4)
    with create_and_delete_hosts([host], test_site):
        yield FILTER_HOST


def test_a_state_filter_narrows_the_table_and_withdrawing_it_widens_it_again(
    dashboard_page: MainDashboard, filter_host: str, test_site: Site
) -> None:
    """A state the host is not in hides it; withdrawing the choice brings it back.

    Filtering on a state the host *is* in would leave the table unchanged and
    prove nothing, so the choice committed here is deliberately the other one.
    The row returning afterwards is what anchors the disappearance: a selector
    that matched nothing at all would fail that half.
    """
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.row_by_host(filter_host)).to_have_count(1)

    state = int(
        test_site.live.query_value(f"GET hosts\nColumns: state\nFilter: name = {filter_host}\n")
    )
    # Any state the host is not in. UP and DOWN are always offered, so one of the
    # two is always available as the excluded choice.
    excluded = "DOWN" if state == 0 else "UP"

    all_hosts.open_filter("State")
    all_hosts.filter_option(excluded).click()
    all_hosts.apply_filter()

    expect(all_hosts.row_by_host(filter_host)).to_have_count(0)

    all_hosts.open_filter("State")
    all_hosts.filter_option(excluded).click()
    all_hosts.apply_filter()

    expect(all_hosts.row_by_host(filter_host)).to_have_count(1)
