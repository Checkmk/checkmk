#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The installer instances, one per connection on the installer socket, whoever connects."""

from tests.testlib.common.utils import wait_until
from tests.testlib.system.host_under_test import HostUnderTest
from tests.testlib.system.systemd import unit_diagnostics

INSTALLER_INSTANCES = "cmk-agent-ctl-installer@*.service"


def _instances(host: HostUnderTest, *states: str) -> list[str]:
    output = host.run(
        [
            "systemctl",
            "list-units",
            "--all",
            "--plain",
            "--no-legend",
            *(f"--state={state}" for state in states),
            INSTALLER_INSTANCES,
        ],
    ).stdout
    return [line.split()[0] for line in output.splitlines() if line.strip()]


def active_instances(host: HostUnderTest) -> list[str]:
    return _instances(host, "active", "activating", "deactivating")


def failed_instances(host: HostUnderTest) -> list[str]:
    return _instances(host, "failed")


def wait_for_installer(host: HostUnderTest) -> None:
    wait_until(
        lambda: not active_instances(host),
        timeout=60,
        interval=0.5,
        condition_name="the installer instance to finish",
    )


def instance_diagnostics(host: HostUnderTest) -> str:
    """What the installer instances of this run said, for the message of a failed assertion."""
    return "\n\n".join(unit_diagnostics(host, unit) for unit in _instances(host)) or (
        "No installer instance is left to show."
    )


def reset_failed_instances(host: HostUnderTest) -> None:
    """Clear the failed instances, which systemd keeps and the suite counts as broken units.

    Fixtures call it before a case as well as after, so that a failed instance can only come from
    the case that looks for one.
    """
    host.run(["systemctl", "reset-failed", INSTALLER_INSTANCES], sudo=True, check=False)
