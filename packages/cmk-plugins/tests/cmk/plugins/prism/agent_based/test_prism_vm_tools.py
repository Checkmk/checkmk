#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import json
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.prism.agent_based.prism_vm import parse_prism_vm_v2
from cmk.plugins.prism.agent_based.prism_vm_tools import (
    check_prism_vm_tools,
    discovery_prism_vm_tools,
)

SECTION = {
    "hostName": "SRV-AHV-02",
    "hypervisorType": "kKvm",
    "ipAddresses": ["192.168.50.42"],
    "memoryCapacityInBytes": 17179869184,
    "memoryReservedCapacityInBytes": 17179869184,
    "numNetworkAdapters": 1,
    "numVCpus": 8,
    "nutanixGuestTools": {
        "applications": {"file_level_restore": False, "vss_snapshot": True},
        "clusterVersion": "2.1.5",
        "communicationLinkActive": True,
        "enabled": True,
        "installedVersion": "2.1.5",
        "toRemove": False,
        "toolsMounted": False,
        "vmId": "0005ce11-a7ca-521d-277a-3cecef5aedf1::7c3694f3-c548-4240-aad4-d5538afa05d5",
        "vmName": "SRV-APP-02",
        "vmUuid": "7c3694f3-c548-4240-aad4-d5538afa05d5",
    },
    "vmName": "SRV-APP-02",
    "vmType": "kGuestVM",
}


@pytest.mark.parametrize(
    ["section", "expected_discovery_result"],
    [
        pytest.param(
            SECTION,
            [
                Service(),
            ],
            id="One service if GuestTools section exists in data.",
        ),
    ],
)
def test_discovery_prism_vm_tools(  # type: ignore[misc]
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_vm_tools(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["params", "section", "expected_check_result"],
    [
        pytest.param(
            {"tools_enabled": "enabled", "tools_install": "installed"},
            SECTION,
            [
                Result(state=State.OK, summary="Tools with version 2.1.5 installed"),
                Result(state=State.OK, summary="Tools enabled"),
            ],
            id="If GuestTools installed and enabled the state is OK.",
        ),
        pytest.param(
            {"tools_enabled": "disabled", "tools_install": "not_installed"},
            SECTION,
            [
                Result(
                    state=State.WARN, summary="Tools with version 2.1.5 installed but should not be"
                ),
                Result(state=State.WARN, summary="Tools enabled, but should be disabled"),
            ],
            id="Tools installed but should not be.",
        ),
    ],
)
def test_check_prism_vm_tools(  # type: ignore[misc]
    params: Mapping[str, Any],
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_vm_tools(
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )


def _v4_section(guest_tools: Mapping[str, object]) -> Mapping[str, Any]:
    vm = {
        "extId": "vm-1",
        "name": "vm-1",
        "hypervisor": "AHV",
        "powerState": "ON",
        "memorySizeBytes": 8589934592,
        "guestTools": guest_tools,
    }
    return parse_prism_vm_v2([[json.dumps(vm)]])


DEFAULT_PARAMS = {"tools_install": "installed", "tools_enabled": "enabled"}


@pytest.mark.parametrize(
    "section",
    [
        pytest.param(
            {"nutanixGuestTools": {"installedVersion": "4.5", "enabled": False}},
            id="legacy agent",
        ),
        pytest.param(
            _v4_section({"version": "4.5", "isInstalled": True, "isEnabled": False}),
            id="v4 agent",
        ),
    ],
)
def test_disabled_tools_that_should_be_enabled_are_warn(  # type: ignore[misc]
    section: Mapping[str, Any],
) -> None:
    assert list(check_prism_vm_tools(params=DEFAULT_PARAMS, section=section)) == [
        Result(state=State.OK, summary="Tools with version 4.5 installed"),
        Result(state=State.WARN, summary="No tools enabled, but should be enabled"),
    ]


def test_vm_without_tools_has_nothing_to_enable() -> None:
    section = {"nutanixGuestTools": {"installedVersion": None, "enabled": False}}

    assert list(
        check_prism_vm_tools(
            params={"tools_install": "not_installed", "tools_enabled": "enabled"},
            section=section,
        )
    ) == [
        Result(state=State.OK, summary="No tools installed"),
        Result(state=State.OK, summary="No tools enabled"),
    ]


def test_vm_without_tools_and_unknown_activation_is_ok() -> None:
    section = {"nutanixGuestTools": {"installedVersion": None, "enabled": None}}

    assert list(
        check_prism_vm_tools(
            params={"tools_install": "not_installed", "tools_enabled": "enabled"},
            section=section,
        )
    ) == [
        Result(state=State.OK, summary="No tools installed"),
        Result(state=State.OK, summary="No tools enabled"),
    ]
