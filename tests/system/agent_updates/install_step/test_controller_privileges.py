#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The controller never holds root's privileges, not even while root installs for it."""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from tests.system.agent_updates.install_step._agent import AGENT_USER, IntegratedUpdaterAgent
from tests.system.agent_updates.install_step._controller import installed_hash
from tests.system.agent_updates.install_step._units import (
    active_instances,
    failed_instances,
    instance_diagnostics,
)
from tests.testlib.common.utils import wait_until
from tests.testlib.system.host_under_test import HostUnderTest
from tests.testlib.system.systemd import CONTROLLER_UNIT, unit_diagnostics

pytestmark = pytest.mark.skip_if_faked_artifacts

_NO_CAPABILITIES = "0000000000000000"
_CONFINEMENT_FIELDS = ("Uid", "CapPrm", "CapEff", "CapBnd", "NoNewPrivs")


def _daemon_confinement(host: HostUnderTest) -> dict[str, str] | None:
    """The PID and the confining fields of /proc/<pid>/status of the controller daemon, or None
    while the unit has no controller process.

    During a restart, MainPID already names systemd's child while it is still root, before it
    applies User= and execs the controller. The Name: field tells that child apart."""
    pid = host.run(
        ["systemctl", "show", "-p", "MainPID", "--value", CONTROLLER_UNIT], sudo=True
    ).stdout.strip()
    status = host.run(["cat", f"/proc/{pid}/status"], sudo=True, check=False).stdout
    fields = dict(line.split(":", 1) for line in status.splitlines() if ":" in line)
    if fields.get("Name", "").strip() != "cmk-agent-ctl":
        return None
    return {"Pid": pid} | {name: " ".join(fields[name].split()) for name in _CONFINEMENT_FIELDS}


def _running_daemon_confinement(host: HostUnderTest) -> dict[str, str]:
    found: list[dict[str, str]] = []

    def daemon_running() -> bool:
        if (confinement := _daemon_confinement(host)) is not None:
            found.append(confinement)
        return bool(found)

    wait_until(daemon_running, timeout=30, interval=0.1, condition_name="the controller daemon")
    return found[0]


@contextmanager
def _update_start_delay_skipped(host: HostUnderTest) -> Iterator[None]:
    """Let a daemon started from here run its first update cycle at once, not after up to a
    minute. systemd passes its own environment on to every unit it starts.

    A daemon started inside keeps the variable after the unset, until its next restart. That only
    takes the start delay from its first cycle, which later cases do not wait for."""
    host.run(["systemctl", "set-environment", "DEBUG_NO_UPDATE_START_DELAY=1"], sudo=True)
    try:
        yield
    finally:
        host.run(["systemctl", "unset-environment", "DEBUG_NO_UPDATE_START_DELAY"], sudo=True)


@pytest.mark.usefixtures("update_offer")
def test_the_controller_holds_no_privileges_while_root_installs(
    host: HostUnderTest, integrated_updater_agent: IntegratedUpdaterAgent
) -> None:
    """TC-AU-023: after an installation the service instance has exited. The controller daemon
    holds no elevated privileges before and after it, and cannot gain any in between.

    The daemon runs the update cycle itself, so the first process read is the one that asks root
    to install. The kernel does not let a process with NoNewPrivs and an empty bounding set gain a
    UID or a capability, so the two fields cover the time between the reads. The test does not
    notice an installation that restarts the daemon under a weaker unit and restores the unit."""
    agent_uid = host.run(["id", "-u", AGENT_USER]).stdout.strip()
    confined = {
        "Uid": " ".join([agent_uid] * 4),
        "CapPrm": _NO_CAPABILITIES,
        "CapEff": _NO_CAPABILITIES,
        "CapBnd": _NO_CAPABILITIES,
        "NoNewPrivs": "1",
    }
    hash_before = installed_hash(host, integrated_updater_agent)

    with _update_start_delay_skipped(host):
        # A started daemon runs its first update cycle within a minute, whatever the interval. A
        # controller that knows DEBUG_NO_UPDATE_START_DELAY runs it at once.
        host.run(["systemctl", "restart", CONTROLLER_UNIT], sudo=True)
    asking = _running_daemon_confinement(host)
    try:
        wait_until(
            lambda: (
                installed_hash(host, integrated_updater_agent) != hash_before
                and not active_instances(host)
            ),
            timeout=180,
            interval=1,
            condition_name="the installation",
        )
    except TimeoutError:
        pytest.fail(
            f"The daemon installed nothing.\n{unit_diagnostics(host, CONTROLLER_UNIT)}\n"
            f"{instance_diagnostics(host)}"
        )
    after = _running_daemon_confinement(host)

    assert not failed_instances(host), (
        f"The installer instance has not exited cleanly.\n{instance_diagnostics(host)}"
    )
    # Installing the agent package restarts the daemon.
    assert asking["Pid"] != after["Pid"], (
        f"The installation did not restart the controller daemon (PID {after['Pid']})."
    )
    # The Uid: line holds the real, effective, saved and filesystem UID. A saved UID of 0 would let
    # the daemon switch back to root, so all four count.
    for when, confinement in (("before", asking), ("after", after)):
        assert {name: confinement[name] for name in confined} == confined, (
            f"The controller daemon is not confined {when} the installation: {confinement}"
        )
