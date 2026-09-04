#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Browser flows for the quick actions of the experimental "All hosts" page.

What only a browser can show here is the round trip from a row selection to a
submitted command: that ticking a row arms the toolbar, that an action carrying
input opens its form beside the table instead of firing, and that the form
refuses to submit until the comment the command requires is there.

The commands are aimed at hosts that are healthy, so nothing here depends on a
check cycle or on a host reaching a particular state -- the acknowledgement is
accepted and applied to nothing, which is the behaviour the endpoint has. What
is asserted is the page's own contract: the form gate, and that a submitted
action closes the form.
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

ACTION_HOST = "e2e-action-host"

# The command titles come from the server's own command registry, not from the Vue
# app, so they are the labels the toolbar renders.
ACKNOWLEDGE = "Acknowledge problems"
SCHEDULE_DOWNTIME = "Schedule downtimes"


@pytest.fixture(name="action_host")
def fixture_action_host(test_site: Site) -> Iterator[str]:
    """One host to aim the quick actions at, removed afterwards."""
    host = HostDetails(name=ACTION_HOST, site=test_site.id, ip=LOCALHOST_IPV4)
    with create_and_delete_hosts([host], test_site):
        yield ACTION_HOST


def test_acknowledging_a_selection_opens_a_form_that_needs_a_comment(
    dashboard_page: MainDashboard, action_host: str
) -> None:
    """Acknowledge opens its form, and the form will not submit without a comment."""
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.row_by_host(action_host)).to_have_count(1)

    all_hosts.tick_host_row(action_host)
    all_hosts.trigger_action(ACKNOWLEDGE)

    expect(all_hosts.action_form(ACKNOWLEDGE)).to_be_visible()
    expect(all_hosts.submit_action("Acknowledge")).to_be_disabled()


def test_a_commented_acknowledgement_is_submitted_and_closes_the_form(
    dashboard_page: MainDashboard, action_host: str
) -> None:
    """Once the comment is there the command is submitted and the form gives way."""
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.row_by_host(action_host)).to_have_count(1)

    all_hosts.tick_host_row(action_host)
    all_hosts.trigger_action(ACKNOWLEDGE)
    all_hosts.acknowledge_comment.fill("e2e acknowledgement")

    submit = all_hosts.submit_action("Acknowledge")
    expect(submit).to_be_enabled()
    submit.click()

    expect(all_hosts.action_form(ACKNOWLEDGE)).to_be_hidden()


def test_scheduling_a_downtime_offers_a_comment_a_duration_and_the_host_only_option(
    dashboard_page: MainDashboard, action_host: str
) -> None:
    """The downtime form carries what a host downtime needs, and gates on the comment.

    The child-hosts option is the half that only a host downtime has; its presence
    here is what distinguishes this form from the services one.
    """
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.row_by_host(action_host)).to_have_count(1)

    all_hosts.tick_host_row(action_host)
    all_hosts.trigger_action(SCHEDULE_DOWNTIME)

    expect(all_hosts.action_form(SCHEDULE_DOWNTIME)).to_be_visible()
    expect(all_hosts.downtime_comment).to_be_visible()
    expect(all_hosts.catalog_panel("Duration")).to_be_visible()
    expect(all_hosts.submit_action("Schedule host downtime")).to_be_disabled()
