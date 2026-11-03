#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Browser flows for the quick actions of the experimental "All hosts" page.

What only a browser can show here is the round trip from a row selection to a
submitted command that reaches the monitoring core. The detail slide-in offers
the same commands for a single host from its own header, and that second route
is covered here too, since it ends in the same place.

The host is put into a problem state up front, because an acknowledgement is
only observable on a host that has one: Checkmk accepts the command for an UP
host and applies it to nothing. The state is forced rather than waited for, and
active checks are paused while it is held, so no recovery clears the
acknowledgement before it is read back off the core.
"""

import logging
from collections.abc import Iterator

import pytest
from playwright.sync_api import expect

from tests.system.gui.testlib.api_helpers import (
    core_checks_paused,
    create_and_delete_hosts,
    LOCALHOST_IPV4,
)
from tests.system.gui.testlib.host_details import HostDetails
from tests.system.gui.testlib.playwright.pom.monitor.all_hosts_experimental import (
    AllHostsExperimental,
)
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.testlib.common.utils import wait_until
from tests.testlib.system.site import Site

logger = logging.getLogger(__name__)

ACTION_HOST = "e2e-action-host"

# The command titles come from the server's own command registry, not from the Vue
# app, so they are the labels the toolbar renders.
ACKNOWLEDGE = "Acknowledge problems"

_HOST_DOWN = 1


def _acknowledged(site: Site, host_name: str) -> int:
    return int(
        site.live.query_value(f"GET hosts\nColumns: acknowledged\nFilter: name = {host_name}\n")
    )


@pytest.fixture(name="action_host")
def fixture_action_host(test_site: Site) -> Iterator[str]:
    """One host in a problem state to aim the quick actions at, removed afterwards.

    Deliberately per-test: both users of this fixture open by asserting the host
    is not acknowledged yet, so sharing it would carry the first one's
    acknowledgement into the second.
    """
    host = HostDetails(name=ACTION_HOST, site=test_site.id, ip=LOCALHOST_IPV4)
    with create_and_delete_hosts([host], test_site), core_checks_paused(test_site):
        test_site.send_host_check_result(ACTION_HOST, _HOST_DOWN, "FAKE DOWN for the action tests")
        yield ACTION_HOST


def test_a_commented_acknowledgement_reaches_the_monitoring_core(
    dashboard_page: MainDashboard, action_host: str, test_site: Site
) -> None:
    """The submitted command is applied to the host, not just accepted by the form.

    The form giving way is the page's own half. The acknowledgement flag on the
    host is the half that proves the command left the browser and reached the
    core, which is the whole reason this scenario sits at the system tier.
    """
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.row_by_host(action_host)).to_have_count(1)
    assert _acknowledged(test_site, action_host) == 0, "the host is acknowledged already"

    all_hosts.tick_host_row(action_host)
    all_hosts.trigger_action(ACKNOWLEDGE)
    all_hosts.acknowledge_comment.fill("e2e acknowledgement")

    all_hosts.submit_action("Acknowledge").click()

    expect(all_hosts.action_form(ACKNOWLEDGE)).to_be_hidden()
    wait_until(
        lambda: _acknowledged(test_site, action_host) == 1,
        timeout=60,
        interval=1,
        condition_name=f"the acknowledgement of {action_host} reaches the core",
    )


def test_acknowledging_from_the_slide_in_reaches_the_monitoring_core(
    dashboard_page: MainDashboard, action_host: str, test_site: Site
) -> None:
    """A command sent from the detail panel is applied to the host it is showing.

    The panel reaches the commands without a row selection, so this is a second
    route to the same core operation rather than a repeat of the toolbar one.
    """
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.row_by_host(action_host)).to_have_count(1)
    assert _acknowledged(test_site, action_host) == 0, "the host is acknowledged already"

    all_hosts.open_slide_in(action_host)
    expect(all_hosts.slide_in).to_be_visible()
    all_hosts.trigger_slide_in_action(ACKNOWLEDGE)
    all_hosts.acknowledge_comment.fill("e2e slide-in acknowledgement")

    all_hosts.submit_action("Acknowledge").click()

    expect(all_hosts.action_form(ACKNOWLEDGE)).to_be_hidden()
    wait_until(
        lambda: _acknowledged(test_site, action_host) == 1,
        timeout=60,
        interval=1,
        condition_name=f"the panel's acknowledgement of {action_host} reaches the core",
    )
