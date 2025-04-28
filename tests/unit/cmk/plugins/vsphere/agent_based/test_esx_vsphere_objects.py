#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Literal

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.vsphere.agent_based.esx_vsphere_objects import (
    check_esx_vsphere_objects,
    check_esx_vsphere_objects_count,
    discovery_esx_vsphere_objects,
    parse_esx_vsphere_objects,
)
from cmk.plugins.vsphere.lib.esx_vsphere_objects import (
    ObjectCountParams,
    ObjectDiscoveryParams,
    StateParams,
    VmInfo,
)

STRING_TABLE = [
    ["hostsystem", "10.1.1.112", "", "poweredOn"],
    ["hostsystem", "10.1.1.111", "", "poweredOn"],
    ["virtualmachine", "Grafana", "10.1.1.111", "poweredOn"],
    ["virtualmachine", "Server", "10.1.1.111", "poweredOff"],
    ["virtualmachine", "virt1-1.4.2", "10.1.1.112", "poweredOff"],
    ["virtualmachine", "Schulungs_ESXi", "10.1.1.112", "poweredOff"],
    ["template", "Dummy-Template", "1.2.3.4", "poweredOff"],
]
STATE_PARAMS = StateParams(unknown=3, poweredOn=0, poweredOff=1, suspended=1, standBy=1)
HOST_VM_SERVICES = [
    Service(item="HostSystem 10.1.1.112"),
    Service(item="HostSystem 10.1.1.111"),
    Service(item="VM Grafana"),
    Service(item="VM Server"),
    Service(item="VM virt1-1.4.2"),
    Service(item="VM Schulungs_ESXi"),
]


def test_parse() -> None:
    assert parse_esx_vsphere_objects(STRING_TABLE) == {
        "HostSystem 10.1.1.112": VmInfo(
            name="10.1.1.112", vmtype="HostSystem", hostsystem="", state="poweredOn"
        ),
        "HostSystem 10.1.1.111": VmInfo(
            name="10.1.1.111", vmtype="HostSystem", hostsystem="", state="poweredOn"
        ),
        "VM Grafana": VmInfo(
            name="Grafana", vmtype="VM", hostsystem="10.1.1.111", state="poweredOn"
        ),
        "VM Server": VmInfo(
            name="Server", vmtype="VM", hostsystem="10.1.1.111", state="poweredOff"
        ),
        "VM virt1-1.4.2": VmInfo(
            name="virt1-1.4.2", vmtype="VM", hostsystem="10.1.1.112", state="poweredOff"
        ),
        "VM Schulungs_ESXi": VmInfo(
            name="Schulungs_ESXi", vmtype="VM", hostsystem="10.1.1.112", state="poweredOff"
        ),
        "Template Dummy-Template": VmInfo(
            name="Dummy-Template", vmtype="Template", hostsystem="1.2.3.4", state="poweredOff"
        ),
    }


@pytest.mark.parametrize(
    ["params", "expected"],
    [
        pytest.param(
            {"templates": True},
            HOST_VM_SERVICES
            + [
                Service(item="Template Dummy-Template"),
            ],
            id="With templates",
        ),
        pytest.param({"templates": False}, HOST_VM_SERVICES, id="Without templates"),
    ],
)
def test_discovery(params: ObjectDiscoveryParams, expected: list[Service]) -> None:
    assert (
        list(
            discovery_esx_vsphere_objects(
                params=params, section=parse_esx_vsphere_objects(STRING_TABLE)
            )
        )
        == expected
    )


@pytest.mark.parametrize(
    ["params", "expected"],
    [
        pytest.param(
            {
                "distribution": [
                    ObjectCountParams(hosts_count=2, state=2, vm_names=["Grafana", "Server"])
                ]
            },
            [
                Result(state=State.OK, summary="Templates: 1"),
                Metric(name="templates", value=1),
                Result(state=State.OK, summary="Virtualmachines: 4"),
                Metric(name="vms", value=4),
                Result(state=State.OK, summary="Hostsystems: 2"),
                Metric(name="hosts", value=2),
                Result(
                    state=State.CRIT,
                    summary="VMs Grafana, Server are running on 1 host: 10.1.1.111",
                ),
            ],
        ),
        pytest.param(
            {
                "distribution": [
                    ObjectCountParams(
                        hosts_count=2, state=2, vm_names=["Grafana", "Schulungs_ESXi"]
                    )
                ]
            },
            [
                Result(state=State.OK, summary="Templates: 1"),
                Metric(name="templates", value=1),
                Result(state=State.OK, summary="Virtualmachines: 4"),
                Metric(name="vms", value=4),
                Result(state=State.OK, summary="Hostsystems: 2"),
                Metric(name="hosts", value=2),
            ],
        ),
        pytest.param(
            {"distribution": []},
            [
                Result(state=State.OK, summary="Templates: 1"),
                Metric(name="templates", value=1),
                Result(state=State.OK, summary="Virtualmachines: 4"),
                Metric(name="vms", value=4),
                Result(state=State.OK, summary="Hostsystems: 2"),
                Metric(name="hosts", value=2),
            ],
        ),
    ],
)
def test_check_count(
    params: Mapping[Literal["distribution"], list[ObjectCountParams]],
    expected: CheckResult,
) -> None:
    assert (
        list(
            check_esx_vsphere_objects_count(
                params=params, section=parse_esx_vsphere_objects(STRING_TABLE)
            )
        )
        == expected
    )


@pytest.mark.parametrize(
    ["item", "params", "expected"],
    [
        pytest.param(
            "HostSystem 10.1.1.111",
            {"states": STATE_PARAMS},
            [Result(state=State.OK, summary="power state: poweredOn")],
        ),
        pytest.param(
            "HostSystem 10.1.1.112",
            {"states": STATE_PARAMS},
            [Result(state=State.OK, summary="power state: poweredOn")],
        ),
        pytest.param(
            "VM Grafana",
            {"states": STATE_PARAMS},
            [
                Result(state=State.OK, summary="power state: poweredOn"),
                Result(state=State.OK, summary="running on [10.1.1.111]"),
            ],
        ),
        pytest.param(
            "VM Schulungs_ESXi",
            {"states": STATE_PARAMS},
            [
                Result(state=State.WARN, summary="power state: poweredOff"),
                Result(state=State.OK, summary="defined on [10.1.1.112]"),
            ],
        ),
        pytest.param(
            "VM Server",
            {"states": STATE_PARAMS},
            [
                Result(state=State.WARN, summary="power state: poweredOff"),
                Result(state=State.OK, summary="defined on [10.1.1.111]"),
            ],
        ),
        pytest.param(
            "VM virt1-1.4.2",
            {"states": STATE_PARAMS},
            [
                Result(state=State.WARN, summary="power state: poweredOff"),
                Result(state=State.OK, summary="defined on [10.1.1.112]"),
            ],
        ),
        pytest.param(
            "Template Dummy-Template",
            {"states": STATE_PARAMS},
            [
                Result(state=State.OK, summary="power state: poweredOff"),
                Result(state=State.OK, summary="defined on [1.2.3.4]"),
            ],
        ),
    ],
)
def test_check(
    item: str, params: Mapping[Literal["states"], StateParams], expected: CheckResult
) -> None:
    assert (
        list(
            check_esx_vsphere_objects(
                item=item, params=params, section=parse_esx_vsphere_objects(STRING_TABLE)
            )
        )
        == expected
    )
