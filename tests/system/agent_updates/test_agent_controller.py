#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The agent controller as systemd runs it."""

from pathlib import PurePosixPath

import pytest

from cmk.ccc.hostaddress import HostName
from tests.testlib.system.agent import (
    clean_up_host,
    controller_connection_json,
    controller_status_json,
    register_controller,
    wait_until_host_receives_data,
)
from tests.testlib.system.host_under_test import HostUnderTest
from tests.testlib.system.site import Site
from tests.testlib.system.systemd import AGENT_SOCKET_UNIT, unit_diagnostics, unit_property

pytestmark = pytest.mark.skip_if_faked_artifacts


def test_dump_through_socket_activation(host: HostUnderTest, agent_ctl: PurePosixPath) -> None:
    """The data path is the real socket unit and a socket-activated agent instance.

    check-mk-agent.socket has Accept=true, so systemd spawns one check-mk-agent@<n>.service
    per connection with the agent's stdin wired to the socket.
    """
    accepted_before = int(unit_property(host, AGENT_SOCKET_UNIT, "NAccepted"))

    res = host.run([agent_ctl.as_posix(), "dump"], sudo=True)

    assert res.stdout.startswith("<<<check_mk>>>")
    assert int(unit_property(host, AGENT_SOCKET_UNIT, "NAccepted")) > accepted_before, (
        f"{AGENT_SOCKET_UNIT} accepted no connection for the dump.\n"
        f"{unit_diagnostics(host, AGENT_SOCKET_UNIT)}"
    )


def test_register_and_fetch_data(host: HostUnderTest, agent_ctl: PurePosixPath, site: Site) -> None:
    hostname = HostName("systemd-agent-host")
    with clean_up_host(site, hostname):
        site.openapi.hosts.create(hostname, attributes={"ipaddress": site.http_address})
        site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)

        register_controller(agent_ctl, site, hostname, host=host)

        connection = controller_connection_json(controller_status_json(agent_ctl, host), site)
        assert connection["remote"]["hostname"] == hostname

        wait_until_host_receives_data(site, hostname)
