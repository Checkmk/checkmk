#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.prism.agent_based.prism_vms import check_prism_vms, discovery_prism_vms

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
def test_discovery_prism_vms(
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
                Result(
                    state=State.OK,
                    notice="Memory 32.0 GiB,\nDescription None,\nProtetion Domain None",
                ),
            ],
            id="If the VM is not in expected state, the check result is WARN.",
        ),
        pytest.param(
            "SRV-FILE-03",
            {"system_state": "on"},
            SECTION,
            [
                Result(state=State.OK, summary="with status on - on Host SRV-AHV-01"),
                Result(
                    state=State.OK,
                    notice="Memory 16.0 GiB,\nDescription None,\nProtetion Domain None",
                ),
            ],
            id="If the VM is in expected state, the check result is OK.",
        ),
    ],
)
def test_check_prism_vms(
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
