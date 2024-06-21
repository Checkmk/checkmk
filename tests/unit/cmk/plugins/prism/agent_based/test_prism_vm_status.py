#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.prism.agent_based.prism_vm_status import (
    check_prism_vm_status,
    discovery_prism_vm_status,
)

SECTION_ONLINE = {
    "acropolisVm": True,
    "consistencyGroupName": None,
    "controlDomain": None,
    "controllerVm": False,
    "cpuReservedInHz": None,
    "description": None,
    "diskCapacityInBytes": 151397597184,
    "displayable": True,
    "fingerPrintOnWrite": "none",
    "gpusInUse": None,
    "guestOperatingSystem": None,
    "hostName": "SRV-AHV-02",
    "hypervisorType": "kKvm",
    "ipAddresses": ["192.168.50.42"],
    "memoryCapacityInBytes": 17179869184,
    "memoryReservedCapacityInBytes": 17179869184,
    "numNetworkAdapters": 1,
    "numVCpus": 8,
    "onDiskDedup": "NONE",
    "powerState": "on",
    "protectionDomainName": None,
    "protectionType": "unprotected",
    "runningOnNdfs": True,
    "vmName": "SRV-APP-02",
    "vmType": "kGuestVM",
}

SECTION_OFFLINE = {
    "acropolisVm": True,
    "consistencyGroupName": None,
    "controlDomain": None,
    "controllerVm": False,
    "cpuReservedInHz": None,
    "description": None,
    "diskCapacityInBytes": 151397597184,
    "displayable": True,
    "fingerPrintOnWrite": "none",
    "gpusInUse": None,
    "guestOperatingSystem": None,
    "hostName": None,
    "hypervisorType": "kKvm",
    "ipAddresses": ["192.168.50.42"],
    "memoryCapacityInBytes": 17179869184,
    "memoryReservedCapacityInBytes": 17179869184,
    "numNetworkAdapters": 1,
    "numVCpus": 8,
    "onDiskDedup": "NONE",
    "powerState": "off",
    "protectionDomainName": None,
    "protectionType": "unprotected",
    "runningOnNdfs": True,
    "vmName": "SRV-APP-02",
    "vmType": "kGuestVM",
}


@pytest.mark.parametrize(
    ["section", "expected_discovery_result"],
    [
        pytest.param(
            SECTION_ONLINE,
            [
                Service(),
            ],
            id="One service if VM data is available.",
        ),
        pytest.param({}, [], id="No service if no data."),
    ],
)
def test_discovery_prism_vm_status(
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_vm_status(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["params", "section", "expected_check_result"],
    [
        pytest.param(
            {"system_state": "on"},
            SECTION_ONLINE,
            [
                Result(state=State.OK, summary="is in state on, defined on SRV-AHV-02"),
                Result(state=State.OK, summary="CPUs: 8, Memory: 16.0 GiB"),
                Result(
                    state=State.OK,
                    notice="Protection Domain: undefined, Protection State: unprotected",
                ),
            ],
            id="If VM is running the state is OK.",
        ),
        pytest.param(
            {"system_state": "off"},
            SECTION_OFFLINE,
            [
                Result(state=State.OK, summary="is in state off, defined on None"),
                Result(state=State.OK, summary="CPUs: 8, Memory: 16.0 GiB"),
                Result(
                    state=State.OK,
                    notice="Protection Domain: undefined, Protection State: unprotected",
                ),
            ],
            id="If VM is offline and should be offline, the state is OK.",
        ),
        pytest.param(
            {"system_state": "on"},
            SECTION_OFFLINE,
            [
                Result(state=State.WARN, summary="is in state off, defined on None"),
                Result(state=State.OK, summary="CPUs: 8, Memory: 16.0 GiB"),
                Result(
                    state=State.OK,
                    notice="Protection Domain: undefined, Protection State: unprotected",
                ),
            ],
            id="If VM is offline but should be running, the state is WARN.",
        ),
    ],
)
def test_check_prism_vm_status(
    params: Mapping[str, Any],
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_vm_status(
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )
