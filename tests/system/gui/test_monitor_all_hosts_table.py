#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Functional E2E tests for the experimental "All hosts" overview table (CMK-34105).

Drives the `cmk-monitoring-all-hosts` Vue app (page `monitor_all_hosts.py`,
"All hosts") in a real browser against a deterministic set of
fixture hosts.

Stability contract (deliberately the *most* reliable slice of the table flows):

  - Assertions are limited to **host names**, **table structure / columns**,
    **search**, **sort order** and **navigation** — all deterministic the
    moment the hosts exist. Monitoring **state** (UP/DOWN/UNREACH) and state
    badge colours are NOT asserted here: they need check cycles and are flaky,
    so they stay manual (see the test plan).
  - Only Playwright auto-waiting expectations (`to_have_count`, `to_have_text`,
    `to_contain_text`, `to_be_visible`) are used — no `time.sleep`, no manual
    polling. The table's settled state is awaited via `to_have_count` on the
    rows before any structural assertion, which absorbs the async initial fetch
    and any server-side re-fetch (sort / search are applied server-side).
  - Host names are distinct and sortable (`e2e-host-a/b/c`) so ordering and
    search subsets are unambiguous.
"""

import json
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

# Distinct, already-sorted host names. The hyphen makes them realistic and also
# exercises the StringCell soft-break path (the raw name is read from the cell
# `title`, not the displayed text, so the injected zero-width spaces do not
# affect the assertions).
HOST_A = "e2e-host-a"
HOST_B = "e2e-host-b"
HOST_C = "e2e-host-c"
ALL_HOST_NAMES = [HOST_A, HOST_B, HOST_C]


@pytest.fixture(name="table_hosts")
def fixture_table_hosts(test_site: Site) -> Iterator[list[str]]:
    """Create three deterministic hosts via the REST API; delete them afterwards.

    No agent is configured — only the host objects themselves are needed for the
    table to render rows, which keeps the fixture fast and deterministic. They do
    carry a resolvable address, without which activation raises a DNS-lookup
    warning and fails the fixture.
    """
    host_details = [
        HostDetails(name=name, site=test_site.id, ip=LOCALHOST_IPV4) for name in ALL_HOST_NAMES
    ]
    with create_and_delete_hosts(host_details, test_site):
        yield ALL_HOST_NAMES


def test_table_renders_all_hosts(dashboard_page: MainDashboard, table_hosts: list[str]) -> None:
    """The table renders every created host as a row, with the key columns.

    Stable assertions: row `to_have_count` equal to the number of fixture
    hosts, each host's row located by its (raw) name, and the key column
    headers present (Host, State, the per-service-state counts and All services).
    """
    all_hosts = AllHostsExperimental(dashboard_page.page)

    # Wait for the table to settle on exactly the fixture rows (absorbs the
    # async initial fetch) before asserting anything else.
    expect(all_hosts.rows()).to_have_count(len(table_hosts))

    for name in table_hosts:
        expect(
            all_hosts.row_by_host(name),
            message=f"Host '{name}' is not rendered as a table row",
        ).to_have_count(1)

    # Key columns exist: Host + State + All services + the per-state counts.
    for header in ("Host", "State", "All services", "OK"):
        expect(
            all_hosts.column_header(header),
            message=f"Column header '{header}' is missing",
        ).to_be_visible()


def test_search_narrows_rows(dashboard_page: MainDashboard, table_hosts: list[str]) -> None:
    """A search term narrows the visible rows; clearing restores them.

    Stable assertions: after searching a substring unique to one host, exactly
    one row remains and it is that host; after clearing, the full set returns.
    Search is applied server-side, so the auto-waiting `to_have_count` absorbs
    the re-fetch.
    """
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.rows()).to_have_count(len(table_hosts))

    # "-host-a" matches only HOST_A by name.
    all_hosts.search("-host-a")
    expect(all_hosts.rows()).to_have_count(1)
    expect(all_hosts.row_by_host(HOST_A)).to_have_count(1)

    # The shared "e2e-host-" prefix matches all three again.
    all_hosts.search("e2e-host-")
    expect(all_hosts.rows()).to_have_count(len(table_hosts))

    # Clearing the search restores the full set.
    all_hosts.search("-host-a")
    expect(all_hosts.rows()).to_have_count(1)
    all_hosts.clear_search()
    expect(all_hosts.rows()).to_have_count(len(table_hosts))


def test_sort_by_host_name_toggles_order(
    dashboard_page: MainDashboard, table_hosts: list[str]
) -> None:
    """Clicking the Host header sorts ascending, then descending.

    Stable assertions: the host name at each row position is ascending after
    the first click and descending after the second. Names are read from the
    cell `title` (the raw value) because `StringCell` injects zero-width spaces
    into the displayed text. Sorting is applied server-side; the auto-waiting
    `to_have_attribute` on each positioned cell absorbs the re-fetch/re-render.
    """
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.rows()).to_have_count(len(table_hosts))

    def expect_name_order(order: list[str]) -> None:
        for index, name in enumerate(order):
            expect(all_hosts.host_name_cell(index)).to_have_attribute("title", name)

    # Ascending: e2e-host-a, e2e-host-b, e2e-host-c
    all_hosts.sort_by("Host")
    expect_name_order(ALL_HOST_NAMES)

    # Descending: reversed. This is the load-bearing half -- the site already answers in
    # ascending name order, so only the second click can show the header drives the order.
    all_hosts.sort_by("Host")
    expect_name_order(list(reversed(ALL_HOST_NAMES)))


def test_total_services_link_navigates_to_host_services(
    dashboard_page: MainDashboard, table_hosts: list[str], test_site: Site
) -> None:
    """A host's "All services" count opens the services page of that host.

    Stable assertions: the count cell's link carries the deterministic `host=<name>` +
    `site=<site>` query and no state narrowing, and following it lands on a URL that carries
    both — independent of any monitoring state.
    """
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.rows()).to_have_count(len(table_hosts))

    expected_url = all_hosts.host_services_page_url(HOST_A, test_site.id)
    total_link = all_hosts.host_total_services_link(HOST_A)
    expect(total_link).to_have_count(1)
    # The link target is deterministic regardless of service state.
    expect(total_link).to_have_attribute("href", expected_url)

    total_link.click()
    all_hosts.page.wait_for_url(lambda url: url.endswith(expected_url))


def test_switching_the_row_limit_asks_the_site_for_the_new_one(
    dashboard_page: MainDashboard, table_hosts: list[str]
) -> None:
    """Changing the offered row limit reaches the site as a fresh listing request.

    The offered tiers start at 1000, so a fixture small enough to run in a browser
    cannot show a *shorter* row set coming back; what is proven here is the half that
    does not need 1001 hosts -- that the choice leaves the page and the table settles
    on the answer. The row-set change itself stays a manual check.
    """
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.rows()).to_have_count(len(table_hosts))

    limits = [option for option in all_hosts.row_limit_options() if option != "All"]
    assert len(limits) > 1, f"the page offers no alternative row limit: {limits}"
    current = all_hosts.row_limit.inner_text().strip()
    target = next(limit for limit in limits if limit != current)

    with all_hosts.page.expect_request(
        lambda request: request.method == "POST" and request.url.endswith("/monitor/hosts")
    ) as listing:
        all_hosts.set_row_limit(target)

    assert json.loads(listing.value.post_data or "{}").get("limit") == int(target)
    expect(all_hosts.rows()).to_have_count(len(table_hosts))
