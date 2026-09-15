#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Browser flows for the quick actions of the experimental "Services of host" page.

The services page shares its action machinery with the hosts page, so what is
worth proving in a browser is what differs: the commands are aimed at services,
and the downtime form therefore withholds the child-hosts option that only a
host downtime has. The comment gate is asserted here too, because it is the
services form that renders it.

Nothing here waits for a state change. The commands are submitted against real
agent-monitored services, and the assertion is the page's own contract -- the
form gate and the form giving way once the command is sent -- not a state the
monitoring core reaches on its own schedule.
"""

import logging
from collections.abc import Iterator

import pytest
from playwright.sync_api import expect

from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.monitor.host_services_experimental import (
    HostServicesExperimental,
)
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

ACKNOWLEDGE = "Acknowledge problems"
SCHEDULE_DOWNTIME = "Schedule downtimes"

# Only a host downtime offers this; a service downtime must not.
CHILD_HOSTS_OPTION = "Only for hosts: Set child hosts in downtime."


@pytest.fixture(name="monitored_host")
def fixture_monitored_host(linux_hosts: list[str]) -> str:
    return linux_hosts[0]


@pytest.fixture(name="services_page")
def fixture_services_page(
    dashboard_page: MainDashboard, monitored_host: str, test_site: Site
) -> Iterator[HostServicesExperimental]:
    page = HostServicesExperimental(dashboard_page.page, monitored_host, test_site.id)
    expect(page.rows().first).to_be_visible()
    yield page


@pytest.fixture(name="a_selected_service")
def fixture_a_selected_service(services_page: HostServicesExperimental) -> str:
    """Tick the first rendered service, whichever the dump produced."""
    name = services_page.rendered_service_names()[0]
    services_page.tick_service_row(name)
    return name


@pytest.mark.usefixtures("a_selected_service")
def test_acknowledging_selected_services_opens_a_form_that_needs_a_comment(
    services_page: HostServicesExperimental,
) -> None:
    services_page.trigger_action(ACKNOWLEDGE)

    expect(services_page.action_form(ACKNOWLEDGE)).to_be_visible()
    expect(services_page.submit_action("Acknowledge")).to_be_disabled()


@pytest.mark.usefixtures("a_selected_service")
def test_a_commented_service_acknowledgement_is_submitted_and_closes_the_form(
    services_page: HostServicesExperimental,
) -> None:
    services_page.trigger_action(ACKNOWLEDGE)
    services_page.acknowledge_comment.fill("e2e service acknowledgement")

    submit = services_page.submit_action("Acknowledge")
    expect(submit).to_be_enabled()
    submit.click()

    expect(services_page.action_form(ACKNOWLEDGE)).to_be_hidden()


@pytest.mark.usefixtures("a_selected_service")
def test_a_service_downtime_offers_no_child_hosts_option(
    services_page: HostServicesExperimental,
) -> None:
    """The child-hosts option belongs to host downtimes and must not appear here.

    The positive half -- that the form itself is on screen with its comment field --
    is asserted alongside, so a renamed form cannot turn the absence check green by
    matching nothing at all.
    """
    services_page.trigger_action(SCHEDULE_DOWNTIME)

    expect(services_page.action_form(SCHEDULE_DOWNTIME)).to_be_visible()
    expect(services_page.downtime_comment).to_be_visible()
    expect(services_page.form_option(CHILD_HOSTS_OPTION)).to_have_count(0)
    expect(services_page.submit_action("Schedule service downtime")).to_be_disabled()
