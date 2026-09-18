#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Browser flows for the quick actions of the experimental "All hosts" page.

What only a browser can show here is the round trip from a row selection to a
submitted command: that ticking a row arms the toolbar, that an action carrying
input opens its form beside the table instead of firing, and that the form
refuses to submit until the comment the command requires is there. The detail
slide-in offers the same commands for a single host from its own header, and
that second route is covered here too, since it ends in the same place.

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
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

ACTION_HOST = "e2e-action-host"
FORM_HOST = "e2e-form-host"

# The command titles come from the server's own command registry, not from the Vue
# app, so they are the labels the toolbar renders.
ACKNOWLEDGE = "Acknowledge problems"
SCHEDULE_DOWNTIME = "Schedule downtimes"

# The downtime form's own labels, as the Vue form renders them.
ADVANCED_SECTION = "Advanced option"
CHILD_HOSTS_OPTION = "Only for hosts: Set child hosts in downtime."
FLEXIBLE_OPTION = (
    "Only start downtime if host/service goes DOWN/UNREACH within the defined start "
    "and end time (flexible)."
)
# The range picker is a flyout: this is the dialog's accessible name, not text it renders.
TIME_RANGE_LABEL = "Downtime time range"

_HOST_DOWN = 1


def _acknowledged(site: Site, host_name: str) -> int:
    return int(
        site.live.query_value(f"GET hosts\nColumns: acknowledged\nFilter: name = {host_name}\n")
    )


@pytest.fixture(name="form_host", scope="module")
def fixture_form_host(test_site: Site) -> Iterator[str]:
    """One host to open the action forms against, shared by the tests that only read them.

    Creating a host costs two activations, so the tests that assert nothing
    about the host's state share one. They need a row to tick and nothing more,
    so this one is left in whatever state its checks give it and no site-wide
    switch is touched on their behalf.
    """
    host = HostDetails(name=FORM_HOST, site=test_site.id, ip=LOCALHOST_IPV4)
    with create_and_delete_hosts([host], test_site):
        yield FORM_HOST


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


def test_acknowledging_a_selection_opens_a_form_that_needs_a_comment(
    dashboard_page: MainDashboard, form_host: str
) -> None:
    """Acknowledge opens its form, and the form will not submit without a comment."""
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.row_by_host(form_host)).to_have_count(1)

    all_hosts.tick_host_row(form_host)
    all_hosts.trigger_action(ACKNOWLEDGE)

    expect(all_hosts.action_form(ACKNOWLEDGE)).to_be_visible()
    expect(all_hosts.submit_action("Acknowledge")).to_be_disabled()


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

    submit = all_hosts.submit_action("Acknowledge")
    expect(submit).to_be_enabled()
    submit.click()

    expect(all_hosts.action_form(ACKNOWLEDGE)).to_be_hidden()
    wait_until(
        lambda: _acknowledged(test_site, action_host) == 1,
        timeout=60,
        interval=1,
        condition_name=f"the acknowledgement of {action_host} reaches the core",
    )


def test_scheduling_a_downtime_offers_a_comment_a_duration_and_the_host_only_option(
    dashboard_page: MainDashboard, form_host: str
) -> None:
    """The downtime form carries what a host downtime needs, and gates on the comment.

    The child-hosts option is the half that only a host downtime has; its presence
    here is what distinguishes this form from the services one.
    """
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.row_by_host(form_host)).to_have_count(1)

    all_hosts.tick_host_row(form_host)
    all_hosts.trigger_action(SCHEDULE_DOWNTIME)

    expect(all_hosts.action_form(SCHEDULE_DOWNTIME)).to_be_visible()
    expect(all_hosts.downtime_comment).to_be_visible()
    expect(all_hosts.catalog_panel("Duration")).to_be_visible()
    # Rendered inside the collapsed Advanced section, so present in the DOM but
    # not on screen - counted rather than seen, which mirrors the absence check
    # the services form gets.
    expect(all_hosts.form_option(CHILD_HOSTS_OPTION)).to_have_count(1)
    expect(all_hosts.submit_action("Schedule host downtime")).to_be_disabled()


def test_the_downtime_advanced_section_offers_child_hosts_and_a_flexible_start(
    dashboard_page: MainDashboard, form_host: str
) -> None:
    """Both host-downtime extras are reachable behind the form's Advanced section.

    The section is collapsed when the form opens, so it is opened here: the
    labels sit in the DOM either way, and only opening it shows they are
    actually offered to a user.
    """
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.row_by_host(form_host)).to_have_count(1)

    all_hosts.tick_host_row(form_host)
    all_hosts.trigger_action(SCHEDULE_DOWNTIME)
    all_hosts.catalog_panel(ADVANCED_SECTION).click()

    expect(all_hosts.form_option(CHILD_HOSTS_OPTION)).to_be_visible()
    expect(all_hosts.form_option(FLEXIBLE_OPTION)).to_be_visible()


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

    submit = all_hosts.submit_action("Acknowledge")
    expect(submit).to_be_enabled()
    submit.click()

    expect(all_hosts.action_form(ACKNOWLEDGE)).to_be_hidden()
    wait_until(
        lambda: _acknowledged(test_site, action_host) == 1,
        timeout=60,
        interval=1,
        condition_name=f"the panel's acknowledgement of {action_host} reaches the core",
    )


def test_a_custom_downtime_duration_offers_an_explicit_start_and_end(
    dashboard_page: MainDashboard, form_host: str
) -> None:
    """The start/end range appears once the Custom duration is chosen.

    The form opens on one of the site's duration presets, so the range is not
    on screen until Custom is picked - the half of the scenario that reading the
    freshly opened form would miss.
    """
    all_hosts = AllHostsExperimental(dashboard_page.page)
    expect(all_hosts.row_by_host(form_host)).to_have_count(1)

    all_hosts.tick_host_row(form_host)
    all_hosts.trigger_action(SCHEDULE_DOWNTIME)
    all_hosts.select_duration("Custom")

    expect(all_hosts.time_range_dialog(TIME_RANGE_LABEL)).to_be_visible()
