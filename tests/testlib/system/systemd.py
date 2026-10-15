#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The agent's systemd units on a host under test."""

import contextlib
import logging
from collections.abc import Iterator
from pathlib import PurePath, PurePosixPath

from tests.testlib.common.utils import wait_until
from tests.testlib.system.host_under_test import HostUnderTest

logger = logging.getLogger(__name__)

CONTROLLER_UNIT = "cmk-agent-ctl-daemon.service"
AGENT_SOCKET_UNIT = "check-mk-agent.socket"
AGENT_SOCKET = PurePosixPath("/run/check-mk-agent.socket")


def unit_property(host: HostUnderTest, unit: str, prop: str) -> str:
    return host.run(["systemctl", "show", "-p", prop, "--value", unit]).stdout.strip()


def unit_is_active(host: HostUnderTest, unit: str) -> bool:
    return host.run(["systemctl", "is-active", unit], check=False).returncode == 0


def unit_journal(host: HostUnderTest, unit: str) -> str:
    return host.run(
        ["journalctl", "--no-pager", "-o", "cat", "-u", unit], sudo=True, check=False
    ).stdout


def unit_diagnostics(host: HostUnderTest, unit: str) -> str:
    status = host.run(["systemctl", "status", "--no-pager", "--full", unit], check=False).stdout
    return f"systemctl status {unit}:\n{status}\n\njournal of {unit}:\n{unit_journal(host, unit)}"


def wait_for_unit_active(host: HostUnderTest, unit: str, timeout: float = 30.0) -> None:
    try:
        wait_until(
            lambda: unit_is_active(host, unit),
            timeout=timeout,
            interval=0.5,
            condition_name=f"{unit} to become active",
        )
    except TimeoutError as excp:
        raise TimeoutError(
            f"{unit} did not become active within {timeout}s.\n{unit_diagnostics(host, unit)}"
        ) from excp


def _clear_controller_connections(host: HostUnderTest, ctl: PurePath) -> None:
    result = host.run([ctl.as_posix(), "delete-all"], sudo=True, check=False)
    if result.returncode != 0:
        logger.warning(
            "%s delete-all exited with %d, registrations may be left over:\n%s",
            ctl,
            result.returncode,
            result.stderr,
        )


def _dump_succeeds(host: HostUnderTest, ctl: PurePath) -> bool:
    return host.run([ctl.as_posix(), "dump"], sudo=True, check=False).returncode == 0


@contextlib.contextmanager
def systemd_managed_agent_controller(host: HostUnderTest, ctl: PurePath) -> Iterator[None]:
    """Wait for the controller that systemd runs, and clear its registrations around the block.

    Nothing is started here. The agent package's postinst enabled and started the units, and
    starting them here would hide exactly the regressions in the maintainer scripts.
    """
    wait_for_unit_active(host, AGENT_SOCKET_UNIT, timeout=10)
    wait_for_unit_active(host, CONTROLLER_UNIT, timeout=30)
    if host.run(["test", "-S", AGENT_SOCKET.as_posix()], check=False).returncode != 0:
        raise RuntimeError(f"{AGENT_SOCKET} was not created by {AGENT_SOCKET_UNIT}")

    _clear_controller_connections(host, ctl)
    wait_until(
        lambda: _dump_succeeds(host, ctl),
        timeout=30,
        interval=0.5,
        condition_name="agent controller to serve a dump",
    )
    try:
        yield
    finally:
        logger.info("Journal of %s:\n%s", CONTROLLER_UNIT, unit_journal(host, CONTROLLER_UNIT))
        _clear_controller_connections(host, ctl)
    # Only after a clean exit, so that this check never hides a failure of the block itself.
    if not unit_is_active(host, CONTROLLER_UNIT):
        raise AssertionError(
            f"{CONTROLLER_UNIT} is no longer active after the block "
            f"(Result={unit_property(host, CONTROLLER_UNIT, 'Result')}, "
            f"NRestarts={unit_property(host, CONTROLLER_UNIT, 'NRestarts')})"
        )
