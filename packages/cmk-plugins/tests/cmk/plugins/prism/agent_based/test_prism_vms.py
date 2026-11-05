#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.prism.agent_based.prism_vms import (
    check_prism_vms,
    discovery_prism_vms,
    parse_prism_vms_v2,
)

SECTION = {
    "SRV-EX-03-restore": {
        "description": None,
        "diskCapacityInBytes": 858993459200,
        "hostName": None,
        "hypervisorType": "kKvm",
        "ipAddresses": [],
        "memoryCapacityInBytes": 34359738368,
        "memoryReservedCapacityInBytes": 0,
        "numNetworkAdapters": 1,
        "numVCpus": 12,
        "powerState": "off",
        "protectionDomainName": None,
        "protectionType": "unprotected",
        "runningOnNdfs": True,
        "vmName": "SRV-EX-03-restore",
        "vmType": "kGuestVM",
    },
    "SRV-FILE-03": {
        "description": None,
        "diskCapacityInBytes": 3103113871360,
        "hostName": "SRV-AHV-01",
        "hypervisorType": "kKvm",
        "ipAddresses": ["192.168.50.44"],
        "memoryCapacityInBytes": 17179869184,
        "memoryReservedCapacityInBytes": 17179869184,
        "numNetworkAdapters": 1,
        "numVCpus": 8,
        "powerState": "on",
        "protectionDomainName": None,
        "protectionType": "unprotected",
        "runningOnNdfs": True,
        "vmName": "SRV-FILE-03",
        "vmType": "kGuestVM",
    },
}


@pytest.mark.parametrize(
    ["section", "expected_discovery_result"],
    [
        pytest.param(
            SECTION,
            [
                Service(item="SRV-EX-03-restore"),
                Service(item="SRV-FILE-03"),
            ],
            id="For every VM, a Service is discovered.",
        ),
    ],
)
def test_discovery_prism_vms(  # type: ignore[misc]
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_vms(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["item", "params", "section", "expected_check_result"],
    [
        pytest.param(
            "SRV-EX-03-restore",
            {"system_state": "on"},
            SECTION,
            [
                Result(state=State.WARN, summary="with status off - on Host None"),
                Result(state=State.OK, notice="Memory 32.0 GiB"),
                Result(state=State.OK, notice="Description None"),
            ],
            id="If the VM is not in expected state, the check result is WARN.",
        ),
        pytest.param(
            "SRV-FILE-03",
            {"system_state": "on"},
            SECTION,
            [
                Result(state=State.OK, summary="with status on - on Host SRV-AHV-01"),
                Result(state=State.OK, notice="Memory 16.0 GiB"),
                Result(state=State.OK, notice="Description None"),
            ],
            id="If the VM is in expected state, the check result is OK.",
        ),
    ],
)
def test_check_prism_vms(  # type: ignore[misc]
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_vms(
                item=item,
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )


# What the v4 agent writes for the 161 VMs recorded on a Prism Central 7.5 lab
RECORDED_V4_SECTION = [
    [
        (
            Path(__file__).parent.parent
            / "special_agent"
            / "v4_fixtures"
            / "section_prism_vms_v2.json"
        ).read_text()
    ]
]


def test_v4_vms_sharing_a_name_get_a_service_each() -> None:
    section = parse_prism_vms_v2(RECORDED_V4_SECTION)

    items = [service.item or "" for service in discovery_prism_vms(section)]

    assert (len(items), [item for item in items if item.startswith("vm-119 ")]) == (
        161,
        ["vm-119 (f9d9ed69)", "vm-119 (5fcd68a4)"],
    )


def test_v4_running_vm_shows_its_host() -> None:
    section = parse_prism_vms_v2(RECORDED_V4_SECTION)

    assert list(check_prism_vms("vm-001 (1f195358)", {"system_state": "on"}, section)) == [
        Result(state=State.OK, summary="with status on - on Host host-2"),
        Result(state=State.OK, notice="Memory 76.0 GiB"),
        Result(state=State.OK, notice="Description description of vm-001"),
    ]


def test_v4_vm_that_is_off_runs_on_no_host() -> None:
    section = parse_prism_vms_v2(RECORDED_V4_SECTION)

    results = list(check_prism_vms("vm-018 (1e187b3a)", {"system_state": "on"}, section))

    assert results[0] == Result(state=State.WARN, summary="with status off - on Host None")


def _v4_vm(power_state: str) -> StringTable:
    vm = {
        "extId": "1f195358-b250-426c-9567-797cdf5e7303",
        "name": "vm",
        "powerState": power_state,
        "memorySizeBytes": 1024**3,
    }
    return [[json.dumps([vm])]]


def test_v4_undetermined_power_state_is_unknown() -> None:
    section = parse_prism_vms_v2(_v4_vm("UNDETERMINED"))

    results = list(check_prism_vms("vm (1f195358)", {"system_state": "on"}, section))

    assert results[0] == Result(state=State.UNKNOWN, summary="with status unknown - on Host None")
