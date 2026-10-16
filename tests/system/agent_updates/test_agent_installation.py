#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Installing the agent package of the site on the host under test."""

from pathlib import Path

import pytest

from tests.testlib.system.agent import install_agent_package_with_output
from tests.testlib.system.host_under_test import HostUnderTest
from tests.testlib.system.systemd import AGENT_SOCKET_UNIT, CONTROLLER_UNIT, unit_is_enabled

pytestmark = pytest.mark.skip_if_faked_artifacts

SUPER_SERVER_SETUP = "/var/lib/cmk-agent/scripts/super-server/setup"

# Messages that mean the systemd deployment took a wrong turn. The maintainer scripts run
# without `set -e` and the dispatcher runs its loop in a pipeline subshell, so none of these
# make the installation exit non-zero.
_FORBIDDEN_INSTALL_OUTPUT = (
    # `[ "$(_systemd_version)" -lt 219 ]` against a systemctl that reports no systemd version
    "Illegal number",
    "Failed to connect to bus",
    "Unable to figure out where to put the systemd units",
    "None of these have been applicable.",
    "Falling back to legacy systemd setup",
)


@pytest.mark.usefixtures("installed_agent_ctl")
def test_installed_agent_reports_data(host: HostUnderTest) -> None:
    output = host.run(["check_mk_agent"], sudo=True).stdout

    assert output.startswith("<<<check_mk>>>"), (
        f"The installed agent does not start its output with the check_mk section.\n{output}"
    )


@pytest.mark.usefixtures("systemd", "agent_not_installed")
def test_install_output_is_clean(host: HostUnderTest, agent_package: Path) -> None:
    installation = install_agent_package_with_output(agent_package, host)
    output = installation.stdout + installation.stderr

    for message in _FORBIDDEN_INSTALL_OUTPUT:
        assert message not in output, (
            f"The agent installation reported {message!r}, so the systemd deployment did not "
            f"take the intended path.\nOutput:\n{output}"
        )

    for unit in (AGENT_SOCKET_UNIT, CONTROLLER_UNIT):
        assert f"Activating systemd unit '{unit}'" in output, (
            f"The agent installation did not report activating {unit}.\nOutput:\n{output}"
        )


@pytest.mark.usefixtures("installed_agent_ctl")
def test_systemd_is_the_deployed_super_server(host: HostUnderTest) -> None:
    deployed = host.run(["/bin/sh", SUPER_SERVER_SETUP, "getdeployed"], sudo=True).stdout.strip()

    assert deployed == "systemd", (
        f'The deployed super server is "{deployed}" rather than "systemd". The agent falls '
        "back to xinetd when its systemd deployment fails."
    )


@pytest.mark.usefixtures("installed_agent_ctl")
def test_super_server_setup_is_repeatable(host: HostUnderTest) -> None:
    """Running deploy and trigger again succeeds and leaves the units enabled."""
    for subcommand in ("deploy", "trigger"):
        result = host.run(["/bin/sh", SUPER_SERVER_SETUP, subcommand], sudo=True, check=False)
        assert result.returncode == 0, (
            f"'{SUPER_SERVER_SETUP} {subcommand}' exited with {result.returncode}.\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        for message in _FORBIDDEN_INSTALL_OUTPUT:
            assert message not in result.stdout + result.stderr, (
                f"'{SUPER_SERVER_SETUP} {subcommand}' reported {message!r}.\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )

    for unit in (AGENT_SOCKET_UNIT, CONTROLLER_UNIT):
        assert unit_is_enabled(host, unit), f"{unit} is no longer enabled"
