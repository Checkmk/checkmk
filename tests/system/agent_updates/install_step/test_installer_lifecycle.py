#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Root code exists only while a package is being installed."""

import pytest

from tests.system.agent_updates.install_step._agent import (
    INSTALLER_SOCKET_UNIT,
    IntegratedUpdaterAgent,
)
from tests.system.agent_updates.install_step._installer import (
    hand_over,
    is_installed,
    MarkerPackage,
    plant_package,
    signature,
)
from tests.system.agent_updates.install_step._units import (
    active_instances,
    instance_diagnostics,
)
from tests.testlib.system.host_under_test import HostUnderTest
from tests.testlib.system.systemd import unit_diagnostics, unit_is_active

pytestmark = pytest.mark.skip_if_faked_artifacts


def test_no_installer_instance_runs_without_an_installation(
    host: HostUnderTest,
    integrated_updater_agent: IntegratedUpdaterAgent,
    marker_package: MarkerPackage,
) -> None:
    """TC-AU-022: with no installation in progress, no installer service instance is running.

    An installation runs first. hand_over waits until its instance has ended, and fails if the
    instance stays."""
    planted = plant_package(host, integrated_updater_agent, marker_package)

    hand_over(
        host, planted, [signature(marker_package.local_path, integrated_updater_agent.trusted_key)]
    )

    assert is_installed(host, marker_package), (
        f"Precondition: the installer did not install the marker package.\n"
        f"{instance_diagnostics(host)}"
    )
    assert unit_is_active(host, INSTALLER_SOCKET_UNIT), unit_diagnostics(
        host, INSTALLER_SOCKET_UNIT
    )
    assert not active_instances(host), (
        f"Installer instances run without an installation: {active_instances(host)}\n"
        f"{instance_diagnostics(host)}"
    )
