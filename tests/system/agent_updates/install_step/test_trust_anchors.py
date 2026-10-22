#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The installer verifies against its own trust anchors, whatever the agent user writes."""

import json
from collections.abc import Iterator
from pathlib import PurePosixPath

import pytest

from tests.system.agent_updates.install_step._agent import (
    generate_signing_key,
    IntegratedUpdaterAgent,
)
from tests.system.agent_updates.install_step._installer import (
    hand_over,
    is_installed,
    MarkerPackage,
    plant_package,
    signature,
    write_as_agent_user,
)
from tests.system.agent_updates.install_step._units import (
    failed_instances,
    instance_diagnostics,
)
from tests.testlib.system.host_under_test import HostUnderTest
from tests.testlib.system.systemd import unit_journal

pytestmark = pytest.mark.skip_if_faked_artifacts

_SIGNATURE_REFUSAL = "no signature of it matches a configured signature key"


def _refused_by_the_signature_check(host: HostUnderTest) -> bool:
    return any(_SIGNATURE_REFUSAL in unit_journal(host, unit) for unit in failed_instances(host))


@pytest.fixture(name="writable_update_config_path")
def _writable_update_config_path(
    host: HostUnderTest, integrated_updater_agent: IntegratedUpdaterAgent
) -> Iterator[PurePosixPath]:
    """A path in the controller's runtime directory, where the agent user may write a second
    update configuration."""
    path = integrated_updater_agent.controller_dir / "cmk-agent-ctl-update.toml"
    yield path
    host.run(["rm", "-f", path.as_posix()], sudo=True)


def test_a_package_signed_with_the_trusted_key_is_installed(
    host: HostUnderTest,
    integrated_updater_agent: IntegratedUpdaterAgent,
    marker_package: MarkerPackage,
) -> None:
    """Without this, a refusal below could come from anything but the signature check."""
    planted = plant_package(host, integrated_updater_agent, marker_package)

    hand_over(
        host, planted, [signature(marker_package.local_path, integrated_updater_agent.trusted_key)]
    )

    assert is_installed(host, marker_package), (
        f"The installer did not install a package signed with the trusted key.\n"
        f"{instance_diagnostics(host)}"
    )
    assert not failed_instances(host), (
        f"The installer instance failed although it installed the package.\n"
        f"{instance_diagnostics(host)}"
    )


def test_a_writable_copy_of_the_update_configuration_has_no_effect(
    host: HostUnderTest,
    integrated_updater_agent: IntegratedUpdaterAgent,
    marker_package: MarkerPackage,
    writable_update_config_path: PurePosixPath,
) -> None:
    """TC-AU-019: a writable copy of the update configuration has no effect."""
    attacker_key = generate_signing_key("attacker")
    write_as_agent_user(
        host,
        f"signature_keys = [{json.dumps(attacker_key.certificate)}]\n",
        writable_update_config_path,
    )
    planted = plant_package(host, integrated_updater_agent, marker_package)

    hand_over(host, planted, [signature(marker_package.local_path, attacker_key)])

    assert not is_installed(host, marker_package), (
        f"The installer installed a package signed with a key that only "
        f"{writable_update_config_path} trusts.\n{instance_diagnostics(host)}"
    )
    assert _refused_by_the_signature_check(host), (
        f"No failed installer instance logged the refusal by the signature check.\n"
        f"{instance_diagnostics(host)}"
    )
