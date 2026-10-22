#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The product's own path to the privileged install step: the controller and its CLI."""

import json
import subprocess

from cmk.ccc.hostaddress import HostName
from tests.system.agent_updates.install_step._agent import AGENT_USER, IntegratedUpdaterAgent
from tests.system.agent_updates.install_step._units import wait_for_installer
from tests.testlib.system.host_under_test import HostUnderTest
from tests.testlib.system.site import Site

UPDATE_HOST = HostName("au-install-step")


def register_for_updates(
    host: HostUnderTest,
    agent: IntegratedUpdaterAgent,
    site: Site,
    hostname: HostName,
) -> None:
    """Register as cmkadmin, who may download every agent, and make the connection the source.

    Without --automatic-updates a registration sets no update source, because the controller's
    default for it is "manual".
    """
    host.run(
        [
            agent.ctl.as_posix(),
            "register",
            "--automatic-updates",
            "--server",
            site.http_address,
            "--site",
            site.id,
            "--hostname",
            hostname,
            "--user",
            "cmkadmin",
            "--password",
            site.admin_password,
            "--trust-cert",
        ],
        sudo=True,
    )


def run_update(
    host: HostUnderTest,
    agent: IntegratedUpdaterAgent,
) -> subprocess.CompletedProcess[str]:
    """Run one update cycle as the agent user, and wait until the installer instance has finished."""
    update = host.run([agent.ctl.as_posix(), "update"], user=AGENT_USER, check=False)
    wait_for_installer(host)
    return update


def installed_hash(host: HostUnderTest, agent: IntegratedUpdaterAgent) -> str:
    """The hash that the controller reports to the site, which offers only a package with
    another hash."""
    return str(json.loads(host.run(["cat", agent.agent_info.as_posix()], sudo=True).stdout)["hash"])
