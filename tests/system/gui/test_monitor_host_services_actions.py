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

The service under test is put into a problem state up front, because an
acknowledgement is only observable on a service that has one. The state is
submitted as a passive result rather than waited for, and active checks are
paused while it is held, so the core keeps it long enough to be read back.
"""

import logging
import re
from collections.abc import Iterator

import pytest
from playwright.sync_api import expect

from tests.system.gui.testlib.api_helpers import core_checks_paused
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.monitor.host_services_experimental import (
    HostServicesExperimental,
)
from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

ACKNOWLEDGE = "Acknowledge problems"
SCHEDULE_DOWNTIME = "Schedule downtimes"

# Only a host downtime offers this; a service downtime must not.
CHILD_HOSTS_OPTION = "Only for hosts: Set child hosts in downtime."

_SERVICE_CRIT = 2


def _assert_filterable(service: str) -> None:
    """A Livestatus request is newline-delimited, and the name is read off the page.

    No service an agent dump produces carries a newline, so this guards the
    assumption rather than escaping for it -- but the same shape unescaped is
    what CMK-38323 is about, and it should not be modelled here.
    """
    assert "\n" not in service, f"service description is not usable in a filter: {service!r}"


def _acknowledged(site: Site, host_name: str, service: str) -> int:
    _assert_filterable(service)
    return int(
        site.live.query_value(
            "GET services\nColumns: acknowledged\n"
            f"Filter: host_name = {host_name}\nFilter: description = {service}\n"
        )
    )


def _downtime_count(site: Site, host_name: str, service: str) -> int:
    _assert_filterable(service)
    return len(
        site.live.query_column(
            "GET downtimes\nColumns: id\n"
            f"Filter: host_name = {host_name}\nFilter: service_description = {service}\n"
        )
    )


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
def fixture_a_selected_service(
    services_page: HostServicesExperimental, monitored_host: str, test_site: Site
) -> Iterator[str]:
    """Tick the first rendered service, held in a problem state.

    Whichever service the agent dump produced will do; what matters is that it
    is not OK, so an acknowledgement against it has something to apply to.
    """
    name = services_page.rendered_service_names()[0]
    with core_checks_paused(test_site):
        test_site.send_service_check_result(
            monitored_host, name, _SERVICE_CRIT, "FAKE CRIT for the action tests"
        )
        services_page.tick_service_row(name)
        try:
            yield name
        finally:
            # The host is module-scoped, and a downtime -- unlike an
            # acknowledgement -- is not cleared by the service recovering. Left
            # behind, it fails the next run's own precondition.
            test_site.openapi.downtimes.delete_by_params(monitored_host, [name])


@pytest.mark.usefixtures("a_selected_service")
def test_acknowledging_selected_services_opens_a_form_that_needs_a_comment(
    services_page: HostServicesExperimental,
) -> None:
    services_page.trigger_action(ACKNOWLEDGE)

    expect(services_page.action_form(ACKNOWLEDGE)).to_be_visible()
    expect(services_page.submit_action("Acknowledge")).to_be_disabled()


def test_a_commented_service_acknowledgement_reaches_the_monitoring_core(
    services_page: HostServicesExperimental,
    a_selected_service: str,
    monitored_host: str,
    test_site: Site,
) -> None:
    """The submitted command is applied to the service, not just accepted.

    The form giving way is the page's own half; the acknowledgement flag on the
    service is what proves the command reached the core. The table is read back
    too, since the state it shows is what a user is left looking at.
    """
    assert _acknowledged(test_site, monitored_host, a_selected_service) == 0, (
        "the service is acknowledged already"
    )

    services_page.trigger_action(ACKNOWLEDGE)
    services_page.acknowledge_comment.fill("e2e service acknowledgement")

    submit = services_page.submit_action("Acknowledge")
    expect(submit).to_be_enabled()
    submit.click()

    expect(services_page.action_form(ACKNOWLEDGE)).to_be_hidden()
    wait_until(
        lambda: _acknowledged(test_site, monitored_host, a_selected_service) == 1,
        timeout=60,
        interval=1,
        condition_name=f"the acknowledgement of {a_selected_service} reaches the core",
    )
    # Retried rather than snapshotted: the table repaints after the action, and
    # ``aria-busy`` clearing marks the fetch, not the render. The tag is spelled
    # either way round depending on the column width.
    expect(services_page.state_cell(a_selected_service)).to_have_text(
        re.compile(r"^\s*(CR|CRITICAL)\s*$")
    )


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
    expect(services_page.catalog_panel("Duration")).to_be_visible()
    expect(services_page.form_option(CHILD_HOSTS_OPTION)).to_have_count(0)
    expect(services_page.submit_action("Schedule service downtime")).to_be_disabled()


def test_a_commented_service_downtime_is_scheduled_in_the_monitoring_core(
    services_page: HostServicesExperimental,
    a_selected_service: str,
    monitored_host: str,
    test_site: Site,
) -> None:
    """Submitting the downtime form puts a downtime on the service in the core.

    Counted on the ``downtimes`` table rather than read off the service's
    downtime depth: a downtime is recorded the moment it is scheduled, while the
    depth only rises once it starts, which depends on the duration chosen.
    """
    assert _downtime_count(test_site, monitored_host, a_selected_service) == 0, (
        "the service carries a downtime already"
    )

    services_page.trigger_action(SCHEDULE_DOWNTIME)
    services_page.downtime_comment.fill("e2e service downtime")

    submit = services_page.submit_action("Schedule service downtime")
    expect(submit).to_be_enabled()
    submit.click()

    expect(services_page.action_form(SCHEDULE_DOWNTIME)).to_be_hidden()
    wait_until(
        lambda: _downtime_count(test_site, monitored_host, a_selected_service) == 1,
        timeout=60,
        interval=1,
        condition_name=f"the downtime for {a_selected_service} reaches the core",
    )
