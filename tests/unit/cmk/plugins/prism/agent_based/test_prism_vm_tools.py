#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State
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
def test_discovery_prism_vm_tools(
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
def test_check_prism_vm_tools(
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
