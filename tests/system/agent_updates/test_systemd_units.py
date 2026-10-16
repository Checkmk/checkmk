#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""State of the systemd units the agent package deploys."""

import pytest

from tests.testlib.system.host_under_test import HostUnderTest
from tests.testlib.system.systemd import (
    AGENT_SOCKET,
    AGENT_SOCKET_UNIT,
    CONTROLLER_UNIT,
    failed_units,
    unit_diagnostics,
    unit_is_active,
    unit_is_enabled,
    unit_journal,
    unit_property,
)

pytestmark = pytest.mark.skip_if_faked_artifacts

AGENT_USER = "cmk-agent"
ASYNC_UNIT = "check-mk-agent-async.service"


@pytest.mark.parametrize("unit", [AGENT_SOCKET_UNIT, CONTROLLER_UNIT, ASYNC_UNIT])
@pytest.mark.usefixtures("installed_agent_ctl")
def test_unit_is_enabled_and_active(host: HostUnderTest, unit: str) -> None:
    assert unit_is_enabled(host, unit), f"{unit} is not enabled.\n{unit_diagnostics(host, unit)}"
    assert unit_is_active(host, unit), f"{unit} is not active.\n{unit_diagnostics(host, unit)}"


@pytest.mark.usefixtures("installed_agent_ctl")
def test_agent_socket_is_the_unix_variant(host: HostUnderTest) -> None:
    """The TCP fallback is what the setup script deploys when the controller is unusable."""
    fragment = unit_property(host, AGENT_SOCKET_UNIT, "FragmentPath")
    assert fragment, (
        f"{AGENT_SOCKET_UNIT} has no unit file.\n{unit_diagnostics(host, AGENT_SOCKET_UNIT)}"
    )

    unit_file = host.run(["cat", fragment]).stdout

    assert f"ListenStream={AGENT_SOCKET}" in unit_file, (
        f"{fragment} does not listen on {AGENT_SOCKET}, so the agent fell back to the TCP "
        f"socket.\n{unit_file}"
    )


@pytest.mark.usefixtures("agent_ctl")
def test_agent_socket_ownership_and_mode(host: HostUnderTest) -> None:
    """The controller refuses to register unless it can write to the agent socket.

    See AgentChannel::operational() in packages/cmk-agent-ctl/src/types.rs, which is what
    SocketUser and SocketMode in check-mk-agent.socket exist to satisfy.
    """
    assert host.run(["test", "-S", AGENT_SOCKET.as_posix()], check=False).returncode == 0, (
        f"{AGENT_SOCKET} is not a socket"
    )

    owner_and_mode = host.run(["stat", "-c", "%U %a", AGENT_SOCKET.as_posix()]).stdout.strip()
    assert owner_and_mode == f"{AGENT_USER} 240", (
        f"{AGENT_SOCKET} is {owner_and_mode!r} rather than '{AGENT_USER} 240'"
    )

    writable = host.run(["test", "-w", AGENT_SOCKET.as_posix()], user=AGENT_USER, check=False)
    assert writable.returncode == 0, f"{AGENT_USER} cannot write to {AGENT_SOCKET}"


@pytest.mark.usefixtures("agent_ctl")
def test_controller_daemon_runs_as_the_agent_user(host: HostUnderTest) -> None:
    assert unit_property(host, CONTROLLER_UNIT, "User") == AGENT_USER

    main_pid = unit_property(host, CONTROLLER_UNIT, "MainPID")
    assert main_pid != "0", (
        f"{CONTROLLER_UNIT} has no main process.\n{unit_diagnostics(host, CONTROLLER_UNIT)}"
    )
    process_user = host.run(["ps", "-o", "user=", "-p", main_pid]).stdout.strip()
    assert process_user == AGENT_USER, (
        f"The controller runs as {process_user!r} rather than {AGENT_USER!r}"
    )


@pytest.mark.usefixtures("installed_agent_ctl")
def test_no_checkmk_unit_failed(host: HostUnderTest) -> None:
    checkmk_failures = [
        unit for unit in failed_units(host) if "check-mk" in unit or "cmk-agent" in unit
    ]

    assert not checkmk_failures, f"Failed Checkmk units: {checkmk_failures}"


@pytest.mark.usefixtures("agent_ctl")
def test_controller_sandbox_is_accepted(host: HostUnderTest) -> None:
    """cmk-agent-ctl-daemon.service carries about fifteen hardening directives.

    Several of them manipulate mount namespaces and /sys, which is where a container is most
    likely to disagree with a real machine. systemd reports such a refusal as "Failed at step
    <NAME>" and then retries, so the unit can look healthy for a while.
    """
    journal = unit_journal(host, CONTROLLER_UNIT)
    assert journal.strip(), (
        f"The journal of {CONTROLLER_UNIT} is empty, so there is nothing to check"
    )

    for message in ("Failed at step", "Failed to set up"):
        assert message not in journal, (
            f"{CONTROLLER_UNIT} reported {message!r}, so systemd could not apply the sandbox "
            f"the unit asks for.\nJournal:\n{journal}"
        )
