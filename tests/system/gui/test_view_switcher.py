#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""E2E guard for the switch between a classic view and its Vue counterpart.

Both switch buttons are rendered by the page they leave and then *teleported*
out of the app root into a host element the page owns -- the title bar, the page
state area, or the page menu bar's shortcut area in the SaaS edition (CMK-38698).
A teleport whose target element is missing mounts nothing and raises nothing, so
the button is simply absent and the only way over is the URL bar.

That failure is invisible below this level: the target selectors live in the
server-rendered page chrome, which no unit test renders. Hence a real browser
round trip -- classic view to the new view and back -- which is also the one user
path both buttons exist for.
"""

import logging

from playwright.sync_api import expect

from tests.system.gui.testlib.playwright.pom.monitor.all_hosts import AllHosts
from tests.system.gui.testlib.playwright.pom.monitor.all_hosts_experimental import (
    AllHostsExperimental,
)
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard

logger = logging.getLogger(__name__)


def test_a_user_can_switch_to_the_new_all_hosts_view_and_back(
    dashboard_page: MainDashboard,
) -> None:
    """Both switch buttons mount where the page can show them, and both navigate.

    One test rather than four: each step only exists once the previous one landed,
    and splitting them would re-drive the same browser round trip for every assert.
    """
    classic = AllHosts(dashboard_page.page)

    expect(classic.try_the_new_view).to_be_visible()

    classic.try_the_new_view.click()
    new_view = AllHostsExperimental(classic.page, navigate_to_page=False)

    expect(new_view.return_to_classic_view).to_be_visible()

    new_view.return_to_classic_view.click()

    expect(classic.try_the_new_view).to_be_visible()
