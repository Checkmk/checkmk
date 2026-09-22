#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""E2E guard for the switch from the classic "All hosts" view to the Vue one.

The button is rendered by the classic view and then *teleported* out of the app
root into a host element the page owns -- the page state area, or the page menu
bar's shortcut area in the SaaS edition (CMK-38698). A teleport whose target
element is missing mounts nothing and raises nothing, so the button is simply
absent and the new view becomes unreachable from the classic one.

That failure is invisible below this level: the target selectors live in the
server-rendered page chrome, which no unit test renders.
"""

import logging

from playwright.sync_api import expect

from tests.system.gui.testlib.playwright.pom.monitor.all_hosts import AllHosts
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard

logger = logging.getLogger(__name__)


def test_a_user_can_switch_from_the_classic_all_hosts_view_to_the_new_one(
    dashboard_page: MainDashboard,
) -> None:
    """The button mounts where the page can show it, and it navigates.

    One test rather than two: the click only exists once the button mounted, and
    splitting would re-drive the same browser round trip for a single assert.
    """
    classic = AllHosts(dashboard_page.page)

    expect(classic.try_the_new_view).to_be_visible()

    classic.try_the_new_view.click()

    expect(classic.main_area.locator(".monitoring-all-hosts-app")).to_be_visible()
