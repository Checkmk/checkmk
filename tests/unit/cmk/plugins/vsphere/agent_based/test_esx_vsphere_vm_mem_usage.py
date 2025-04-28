#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from tests.unit.cmk.plugins.vsphere.agent_based.esx_vsphere_vm_util import esx_vm_section

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Metric, Result, Service, State
from cmk.plugins.vsphere.agent_based import esx_vsphere_vm, esx_vsphere_vm_mem_usage
from cmk.plugins.vsphere.lib import esx_vsphere


@pytest.mark.parametrize(
    ["vm_values", "expected_result"],
    [
        pytest.param(
            {
                "summary.quickStats.hostMemoryUsage": ["1"],
                "summary.quickStats.guestMemoryUsage": ["1"],
                "summary.quickStats.balloonedMemory": ["1"],
                "summary.quickStats.sharedMemory": ["1"],
                "summary.quickStats.privateMemory": ["1"],
            },
            esx_vsphere.ESXMemory(
                host_usage=1048576.0,
                guest_usage=1048576.0,
                ballooned=1048576.0,
                private=1048576.0,
                shared=1048576.0,
            ),
            id="data from vCenter",
        ),
        pytest.param(
            {
                "summary.quickStats.hostMemoryUsage": ["1"],
                "summary.quickStats.guestMemoryUsage": ["1"],
                "summary.quickStats.balloonedMemory": ["0"],
                "summary.quickStats.sharedMemory": ["0"],
            },
            esx_vsphere.ESXMemory(
                host_usage=1048576.0,
                guest_usage=1048576.0,
                ballooned=0,
                private=None,
                shared=0,
            ),
            id="data from ESX host",
        ),
    ],
)
def test_parse_esx_vsphere_memory(
    vm_values: Mapping[str, Sequence[str]],
    expected_result: esx_vsphere.ESXMemory,
) -> None:
    assert esx_vsphere_vm._parse_esx_memory_section(vm_values) == expected_result


@pytest.mark.parametrize(
    ["section", "expected_result"],
    [
        pytest.param(
            esx_vm_section(
                memory=None,
                power_state="poweredOff",
            ),
            [],
            id="off",
        ),
        pytest.param(
            esx_vm_section(
                memory=esx_vsphere.ESXMemory(
                    host_usage=1,
                    guest_usage=1,
                    ballooned=1,
                    private=1,
                    shared=1,
                ),
                power_state="poweredOn",
            ),
            [
                Service(),
            ],
            id="data from vCenter",
        ),
    ],
)
def test_discovery_mem_usage(
    section: esx_vsphere.SectionESXVm, expected_result: DiscoveryResult
) -> None:
    assert list(esx_vsphere_vm_mem_usage.discovery_mem_usage(section)) == expected_result


@pytest.mark.parametrize(
    ["section", "expected_result"],
    [
        pytest.param(
            esx_vm_section(
                memory=None,
                power_state="poweredOff",
            ),
            [
                Result(state=State.OK, summary="VM is poweredOff, skipping this check"),
            ],
            id="off",
        ),
        pytest.param(
            esx_vm_section(
                memory=esx_vsphere.ESXMemory(
                    host_usage=1,
                    guest_usage=1,
                    ballooned=1,
                    private=1,
                    shared=1,
                ),
                power_state="poweredOn",
            ),
            [
                Result(state=State.OK, summary="Host: 1 B"),
                Metric("host", 1.0),
                Result(state=State.OK, summary="Guest: 1 B"),
                Metric("guest", 1.0),
                Result(state=State.OK, summary="Ballooned: 1 B"),
                Metric("ballooned", 1.0),
                Result(state=State.OK, summary="Private: 1 B"),
                Metric("private", 1.0),
                Result(state=State.OK, summary="Shared: 1 B"),
                Metric("shared", 1.0),
            ],
            id="data from vCenter",
        ),
        pytest.param(
            esx_vm_section(
                memory=esx_vsphere.ESXMemory(
                    host_usage=1,
                    guest_usage=1,
                    ballooned=0,
                    private=None,
                    shared=0,
                ),
                power_state="poweredOn",
            ),
            [
                Result(state=State.OK, summary="Host: 1 B"),
                Metric("host", 1.0),
                Result(state=State.OK, summary="Guest: 1 B"),
                Metric("guest", 1.0),
                Result(state=State.OK, summary="Ballooned: 0 B"),
                Metric("ballooned", 0.0),
                Result(state=State.OK, summary="Shared: 0 B"),
                Metric("shared", 0.0),
            ],
            id="data from ESX host",
        ),
    ],
)
def test_check_memory_usage(
    section: esx_vsphere.SectionESXVm, expected_result: CheckResult
) -> None:
    assert (
        list(
            esx_vsphere_vm_mem_usage.check_mem_usage(
                {},
                section,
            )
        )
        == expected_result
    )
