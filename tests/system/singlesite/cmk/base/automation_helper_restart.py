#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess

from tests.testlib.common.utils import wait_until
from tests.testlib.system.site import Site


def restart_automation_helper_and_wait_until_reachable(site: Site) -> None:
    """Restart the automation helper, e.g. to make it load newly added plug-ins.

    The automation helper loads the plug-ins only once, and does not watch the
    plug-in directories. Service discovery via the REST API is executed by the
    automation helper, so it will not see plug-ins added to the site otherwise.
    """

    def automation_helper_socket_reachable() -> bool:
        try:
            site.python_helper("_helper_connect_to_automation_helper_socket.py").check_output()
        except subprocess.CalledProcessError:
            return False
        return True

    site.omd("restart", "automation-helper")
    wait_until(
        automation_helper_socket_reachable,
        timeout=10,
        interval=0.25,
    )
