#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""What reinstalling and removing the agent package does to the systemd units."""

from collections.abc import Iterator
from pathlib import Path, PurePosixPath

import pytest

from cmk.ccc.hostaddress import HostName
from tests.testlib.system.agent import (
    clean_up_host,
    controller_connection_json,
    controller_status_json,
    install_agent_package,
    register_controller,
    uninstall_agent_package,
    wait_until_host_receives_data,
)
from tests.testlib.system.host_under_test import HostUnderTest
from tests.testlib.system.site import Site
from tests.testlib.system.systemd import (
    AGENT_SOCKET,
    AGENT_SOCKET_UNIT,
    CONTROLLER_UNIT,
    failed_units,
    unit_diagnostics,
    unit_is_active,
    unit_property,
    wait_for_unit_active,
)

pytestmark = pytest.mark.skip_if_faked_artifacts


@pytest.mark.usefixtures("agent_ctl")
def test_reinstall_restarts_the_controller(host: HostUnderTest, agent_package: Path) -> None:
    """prerm stops and disables the units before postinst enables and restarts them.

    That makes a reinstall of the same version a real stop and start cycle, not a no-op.
    """
    pid_before = unit_property(host, CONTROLLER_UNIT, "MainPID")
    assert pid_before != "0", (
        f"{CONTROLLER_UNIT} has no main process before the reinstall.\n"
        f"{unit_diagnostics(host, CONTROLLER_UNIT)}"
    )

    install_agent_package(agent_package, host)

    wait_for_unit_active(host, CONTROLLER_UNIT, timeout=30)
    assert unit_property(host, CONTROLLER_UNIT, "MainPID") != pid_before, (
        f"{CONTROLLER_UNIT} kept its main process across the reinstall, so prerm did not "
        f"stop it.\n{unit_diagnostics(host, CONTROLLER_UNIT)}"
    )


def test_registration_survives_reinstall(
    host: HostUnderTest, agent_ctl: PurePosixPath, site: Site, agent_package: Path
) -> None:
    hostname = HostName("systemd-agent-reinstall")
    with clean_up_host(site, hostname):
        site.openapi.hosts.create(hostname, attributes={"ipaddress": site.http_address})
        site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
        register_controller(agent_ctl, site, hostname, host=host)
        wait_until_host_receives_data(site, hostname)

        install_agent_package(agent_package, host)

        wait_for_unit_active(host, CONTROLLER_UNIT, timeout=30)
        connection = controller_connection_json(controller_status_json(agent_ctl, host), site)
        assert connection["remote"]["hostname"] == hostname, (
            f"The registration for {hostname} did not survive the reinstall.\n{connection}"
        )
        wait_until_host_receives_data(site, hostname)


@pytest.fixture(name="reinstalled_after_test")
def _reinstalled_after_test(host: HostUnderTest, agent_package: Path) -> Iterator[None]:
    try:
        yield
    finally:
        install_agent_package(agent_package, host)


@pytest.mark.usefixtures("reinstalled_after_test")
def test_uninstall_removes_the_units(
    host: HostUnderTest, installed_agent_ctl: PurePosixPath
) -> None:
    uninstall_agent_package(host=host)

    unit_files = host.run(["systemctl", "list-unit-files", "--no-legend", "--plain"]).stdout
    leftovers = [
        line.split()[0]
        for line in unit_files.splitlines()
        if "check-mk" in line or "cmk-agent" in line
    ]
    assert not leftovers, f"Uninstalling the agent left these unit files behind: {leftovers}"

    for unit in (CONTROLLER_UNIT, AGENT_SOCKET_UNIT):
        assert not unit_is_active(host, unit), f"{unit} is still active after the uninstall"
    assert host.run(["test", "-e", installed_agent_ctl.as_posix()], check=False).returncode != 0, (
        f"{installed_agent_ctl} was not removed"
    )

    host.run(["systemctl", "daemon-reload"], sudo=True)
    checkmk_failures = [
        unit for unit in failed_units(host) if "check-mk" in unit or "cmk-agent" in unit
    ]
    assert not checkmk_failures, f"Failed Checkmk units after the uninstall: {checkmk_failures}"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="CMK-40839")
@pytest.mark.usefixtures("installed_agent_ctl", "reinstalled_after_test")
def test_uninstall_removes_the_socket_file(host: HostUnderTest) -> None:
    uninstall_agent_package(host=host)

    assert host.run(["test", "-e", AGENT_SOCKET.as_posix()], check=False).returncode != 0, (
        f"{AGENT_SOCKET} still exists after the uninstall"
    )
