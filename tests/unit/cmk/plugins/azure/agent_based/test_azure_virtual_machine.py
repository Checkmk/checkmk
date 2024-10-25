#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.azure.agent_based.azure_virtual_machine import (
    _MAP_STATES,
    check_azure_virtual_machine,
    check_azure_virtual_machine_summary,
    check_azure_vm_burst_cpu_credits,
    check_azure_vm_cpu_utilization,
    check_azure_vm_disk,
    check_azure_vm_memory,
    check_azure_vm_network_io,
    discover_azure_virtual_machine,
    discover_azure_virtual_machine_summary,
    discover_azure_vm_cpu_utilization,
    discover_azure_vm_network_io,
    VMSummaryParams,
)
from cmk.plugins.lib import interfaces
from cmk.plugins.lib.azure import AzureMetric, Resource, Section

SECTION = {
    "VM-test-1": Resource(
        id="/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourceGroups/test1/providers/Microsoft.Compute/virtualMachines/VM-test-1",
        name="VM-test-1",
        type="Microsoft.Compute/virtualMachines",
        group="test1",
        kind=None,
        location="uksouth",
        tags={},
        properties={},
        specific_info={
            "statuses": [
                {
                    "code": "ProvisioningState/succeeded",
                    "level": "Info",
                    "displayStatus": "Provisioning succeeded",
                    "time": "2023-02-09T16:19:16.9149346+00:00",
                },
                {"code": "PowerState/running", "level": "Info", "displayStatus": "VM running"},
            ]
        },
        metrics={
            "average_Percentage_CPU": AzureMetric(
                name="Percentage CPU", aggregation="average", value=0.275, unit="percent"
            ),
            "average_CPU_Credits_Consumed": AzureMetric(
                name="CPU Credits Consumed", aggregation="average", value=0, unit="count"
            ),
            "average_CPU_Credits_Remaining": AzureMetric(
                name="CPU Credits Remaining", aggregation="average", value=101.21, unit="count"
            ),
            "average_Available_Memory_Bytes": AzureMetric(
                name="Available Memory Bytes", aggregation="average", value=206569472, unit="bytes"
            ),
            "average_Disk_Read_Operations/Sec": AzureMetric(
                name="Disk Read Operations/Sec",
                aggregation="average",
                value=0,
                unit="countpersecond",
            ),
            "average_Disk_Write_Operations/Sec": AzureMetric(
                name="Disk Write Operations/Sec",
                aggregation="average",
                value=0.33,
                unit="countpersecond",
            ),
            "total_Disk_Read_Bytes": AzureMetric(
                name="Disk Read Bytes", aggregation="total", value=0, unit="bytes"
            ),
            "total_Disk_Write_Bytes": AzureMetric(
                name="Disk Write Bytes", aggregation="total", value=286887.79, unit="bytes"
            ),
            "total_Network_In_Total": AzureMetric(
                name="Network In Total", aggregation="total", value=38778, unit="bytes"
            ),
            "total_Network_Out_Total": AzureMetric(
                name="Network Out Total", aggregation="total", value=55957, unit="bytes"
            ),
        },
        subscription="4db89361-bcd9-4353-8edb-33f49608d4fa",
    )
}

MULTIPLE_VMS_SECTION = {
    "VM-test-1": Resource(
        id="/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourceGroups/test1/providers/Microsoft.Compute/virtualMachines/VM-test-1",
        name="VM-test-1",
        type="Microsoft.Compute/virtualMachines",
        group="test1",
        kind=None,
        location="uksouth",
        tags={},
        properties={},
        specific_info={
            "statuses": [
                {
                    "code": "ProvisioningState/succeeded",
                    "level": "Info",
                    "displayStatus": "Provisioning succeeded",
                    "time": "2023-02-09T16:19:16.9149346+00:00",
                },
                {
                    "code": "PowerState/running",
                    "level": "Info",
                    "displayStatus": "VM running",
                },
            ]
        },
        metrics={},
        subscription="4db89361-bcd9-4353-8edb-33f49608d4fa",
    ),
    "VM-test-2": Resource(
        id="/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourceGroups/test1/providers/Microsoft.Compute/virtualMachines/VM-test-2",
        name="VM-test-2",
        type="Microsoft.Compute/virtualMachines",
        group="test1",
        kind=None,
        location="westeurope",
        tags={},
        properties={},
        specific_info={
            "statuses": [
                {
                    "code": "ProvisioningState/succeeded",
                    "level": "Info",
                    "displayStatus": "Provisioning succeeded",
                    "time": "2023-02-09T16:23:24.032408+00:00",
                },
                {
                    "code": "PowerState/running",
                    "level": "Info",
                    "displayStatus": "VM running",
                },
            ]
        },
        metrics={},
        subscription="4db89361-bcd9-4353-8edb-33f49608d4fa",
    ),
}


@pytest.mark.parametrize(
    "section,expected_discovery",
    [
        pytest.param(
            MULTIPLE_VMS_SECTION,
            [Service(item="VM-test-1"), Service(item="VM-test-2")],
            id="multiple VM resources",
        ),
        pytest.param({}, [], id="no VM resources"),
    ],
)
def test_discover_azure_virtual_machine(
    section: Section,
    expected_discovery: DiscoveryResult,
) -> None:
    assert list(discover_azure_virtual_machine(section)) == expected_discovery


@pytest.mark.parametrize(
    "item,params,section,expected_result",
    [
        pytest.param(
            "VM-test-1",
            _MAP_STATES,
            SECTION,
            [
                Result(state=State.OK, summary="Provisioning succeeded"),
                Result(state=State.OK, summary="VM running"),
                Result(state=State.OK, summary="Location: uksouth"),
            ],
            id="statuses present, no message",
        ),
        pytest.param(
            "VM-test-1",
            _MAP_STATES,
            {
                "VM-test-1": Resource(
                    id="/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourceGroups/test-group/providers/Microsoft.Compute/virtualMachines/VM-test-1",
                    name="VM-test-1",
                    type="Microsoft.Compute/virtualMachines",
                    group="test-group",
                    kind=None,
                    location="uksouth",
                    tags={},
                    properties={},
                    specific_info={},
                    metrics={},
                    subscription="4db89361-bcd9-4353-8edb-33f49608d4fa",
                ),
            },
            [
                Result(state=State.WARN, summary="Provisioning unknown"),
                Result(state=State.UNKNOWN, summary="VM unknown"),
                Result(state=State.OK, summary="Location: uksouth"),
            ],
            id="missing statusses",
        ),
        pytest.param(
            "VM-test-1",
            _MAP_STATES,
            {
                "VM-test-1": Resource(
                    id="/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourceGroups/test-group/providers/Microsoft.Compute/virtualMachines/VM-test-1",
                    name="VM-test-1",
                    type="Microsoft.Compute/virtualMachines",
                    group="test-group",
                    kind=None,
                    location="uksouth",
                    tags={},
                    properties={},
                    specific_info={
                        "statuses": [
                            {
                                "code": "ProvisioningState/-",
                                "level": "Info",
                                "displayStatus": "Provisioning succeeded",
                                "time": "2023-02-09T16:19:16.9149346+00:00",
                                "message": "Unknown provisioning",
                            },
                            {
                                "code": "PowerState/-",
                                "level": "Info",
                                "displayStatus": "VM running",
                                "message": "Error happened",
                            },
                        ]
                    },
                    metrics={},
                    subscription="4db89361-bcd9-4353-8edb-33f49608d4fa",
                ),
            },
            [
                Result(state=State.WARN, summary="Provisioning unknown (Unknown provisioning)"),
                Result(state=State.UNKNOWN, summary="VM unknown (Error happened)"),
                Result(state=State.OK, summary="Location: uksouth"),
            ],
            id="statuses unknown, messages present",
        ),
        pytest.param(
            "VM-test-1",
            _MAP_STATES,
            {
                "VM-test-1": Resource(
                    id="/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourceGroups/test-group/providers/Microsoft.Compute/virtualMachines/VM-test-1",
                    name="VM-test-1",
                    type="Microsoft.Compute/virtualMachines",
                    group="test-group",
                    kind=None,
                    location="uksouth",
                    tags={},
                    properties={},
                    specific_info={
                        "statuses": [
                            {
                                "level": "Info",
                                "displayStatus": "Provisioning succeeded",
                                "time": "2023-02-09T16:19:16.9149346+00:00",
                                "message": "Unknown provisioning",
                            },
                            {
                                "level": "Info",
                                "displayStatus": "VM running",
                                "message": "Error happened",
                            },
                        ]
                    },
                    metrics={},
                    subscription="4db89361-bcd9-4353-8edb-33f49608d4fa",
                ),
            },
            [
                Result(state=State.WARN, summary="Provisioning unknown"),
                Result(state=State.UNKNOWN, summary="VM unknown"),
                Result(state=State.OK, summary="Location: uksouth"),
            ],
            id="statuses without code",
        ),
    ],
)
def test_check_azure_virtual_machines(
    item: str,
    params: Mapping[str, int],
    section: Section,
    expected_result: CheckResult,
) -> None:
    assert (
        list(check_azure_virtual_machine(item=item, params=params, section=section))
        == expected_result
    )


def test_check_azure_virtual_machines_no_item() -> None:
    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(check_azure_virtual_machine(item="VM-test-1", params={}, section={}))


@pytest.mark.parametrize(
    "section,expected_discovery",
    [
        pytest.param(MULTIPLE_VMS_SECTION, [Service()], id="multiple VM resources"),
        pytest.param({}, [], id="no VM resources"),
    ],
)
def test_discover_azure_virtual_machines_summary(
    section: Section,
    expected_discovery: DiscoveryResult,
) -> None:
    assert list(discover_azure_virtual_machine_summary(section)) == expected_discovery


@pytest.mark.parametrize(
    "params,section,expected_result",
    [
        pytest.param(
            {
                "levels_provisioning": {"succeeded": {"levels": (2, 3)}},
                "levels_power": {"running": {"levels": (1, 2)}},
            },
            MULTIPLE_VMS_SECTION,
            [
                Result(state=State.WARN, summary="Provisioning: 2 succeeded (warn/crit at 2/3)"),
                Result(state=State.CRIT, summary="Power states: 2 running (warn/crit at 1/2)"),
                Result(
                    state=State.OK,
                    notice="VM-test-1: Provisioning succeeded, VM running",
                ),
                Result(
                    state=State.OK,
                    notice="VM-test-2: Provisioning succeeded, VM running",
                ),
            ],
            id="check upper levels",
        ),
        pytest.param(
            {
                "levels_provisioning": {"failed": {"levels_lower": (2, 1)}},
                "levels_power": {"stopped": {"levels_lower": (1, -1)}},
            },
            MULTIPLE_VMS_SECTION,
            [
                Result(
                    state=State.CRIT,
                    summary="Provisioning: 0 failed (warn/crit below 2/1) / 2 succeeded",
                ),
                Result(
                    state=State.WARN,
                    summary="Power states: 2 running / 0 stopped (warn/crit below 1/-1)",
                ),
                Result(
                    state=State.OK,
                    notice="VM-test-1: Provisioning succeeded, VM running",
                ),
                Result(
                    state=State.OK,
                    notice="VM-test-2: Provisioning succeeded, VM running",
                ),
            ],
            id="check lower levels",
        ),
    ],
)
def test_check_azure_virtual_machines_summary(
    section: Section,
    params: Mapping[str, VMSummaryParams],
    expected_result: CheckResult,
) -> None:
    assert (
        list(check_azure_virtual_machine_summary(params=params, section=section)) == expected_result
    )


@pytest.mark.parametrize(
    "section, expected_discovery",
    [
        pytest.param(SECTION, [Service(item="CPU Utilization")], id="one resource"),
        pytest.param(MULTIPLE_VMS_SECTION, [], id="multiple resources"),
        pytest.param({}, [], id="no resources"),
    ],
)
def test_discover_azure_vm_cpu_utilization(
    section: Section, expected_discovery: DiscoveryResult
) -> None:
    assert list(discover_azure_vm_cpu_utilization(section)) == expected_discovery


@pytest.mark.parametrize(
    "params,section,expected_result",
    [
        (
            {"levels": (0.2, 0.5)},
            SECTION,
            [
                Result(
                    state=State.WARN, summary="CPU utilization: 0.28% (warn/crit at 0.20%/0.50%)"
                ),
                Metric("util", 0.275, levels=(0.2, 0.5)),
            ],
        ),
    ],
)
def test_check_azure_vm_cpu_utilization(
    params: Mapping[str, tuple[float, float]], section: Section, expected_result: CheckResult
) -> None:
    assert (
        list(check_azure_vm_cpu_utilization("CPU Utilization", params, section)) == expected_result
    )


@pytest.mark.parametrize(
    "params,section,expected_result",
    [
        (
            {"levels": (200.0, 150.0)},
            SECTION,
            [
                Result(state=State.OK, summary="Consumed: 0"),
                Metric("cpu_credits_consumed", 0.0),
                Result(state=State.CRIT, summary="Remaining: 101.21 (warn/crit below 200.0/150.0)"),
                Metric("cpu_credits_remaining", 101.21),
            ],
        ),
    ],
)
def test_check_azure_vm_burst_cpu_credits(
    params: Mapping[str, tuple[float, float]], section: Section, expected_result: CheckResult
) -> None:
    assert list(check_azure_vm_burst_cpu_credits(params, section)) == expected_result


@pytest.mark.parametrize(
    "params,section,expected_result",
    [
        (
            {"levels": (1000, 1000000000)},
            SECTION,
            [
                Result(
                    state=State.CRIT,
                    summary="Available memory: 197 MiB (warn/crit below 1000 B/954 MiB)",
                ),
                Metric("mem_available", 206569472.0),
            ],
        ),
    ],
)
def test_check_azure_vm_memory(
    params: Mapping[str, tuple[float, float]], section: Section, expected_result: CheckResult
) -> None:
    assert list(check_azure_vm_memory(params, section)) == expected_result


@pytest.mark.parametrize(
    "params,section,expected_result",
    [
        (
            {"disk_write_ios": (0.2, 0.5)},
            SECTION,
            [
                Result(state=State.OK, summary="Read: 0.00 B/s"),
                Metric("disk_read_throughput", 0.0),
                Result(state=State.OK, summary="Write: 4.78 kB/s"),
                Metric("disk_write_throughput", 4781.463166666666),
                Result(state=State.OK, summary="Read operations: 0.00/s"),
                Metric("disk_read_ios", 0.0),
                Result(
                    state=State.WARN,
                    summary="Write operations: 0.33/s (warn/crit at 0.20/s/0.50/s)",
                ),
                Metric("disk_write_ios", 0.33, levels=(0.2, 0.5)),
            ],
        ),
    ],
)
def test_check_azure_vm_disk(
    params: Mapping[str, tuple[float, float]], section: Section, expected_result: CheckResult
) -> None:
    assert list(check_azure_vm_disk(params, section)) == expected_result


@pytest.mark.parametrize(
    "section, expected_discovery",
    [
        pytest.param(SECTION, [Service(item="Network IO")], id="one resource"),
        pytest.param(MULTIPLE_VMS_SECTION, [], id="multiple resources"),
        pytest.param({}, [], id="no resources"),
    ],
)
def test_discover_azure_vm_network_io(
    section: Section, expected_discovery: DiscoveryResult
) -> None:
    assert list(discover_azure_vm_network_io(section)) == expected_discovery


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "params,section,expected_result",
    [
        (
            interfaces.CHECK_DEFAULT_PARAMETERS,
            SECTION,
            [
                Result(state=State.OK, summary="[0]"),
                Result(state=State.OK, summary="(up)", details="Operational state: up"),
                Result(state=State.OK, summary="Speed: unknown"),
                Result(state=State.OK, summary="In: 646 B/s"),
                Metric("in", 646.3, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Out: 933 B/s"),
                Metric("out", 932.6166666666667, boundaries=(0.0, None)),
            ],
        ),
        pytest.param(
            interfaces.CHECK_DEFAULT_PARAMETERS,
            {
                "name": Resource(
                    "id",
                    "name",
                    "Microsoft.Compute/virtualMachines",
                    "consulting",
                    None,
                    "westeurope",
                    {},
                    {},
                    {"statuses": ["Max recursion depth reached", "Max recursion depth reached"]},
                    {},
                    "some_hash",
                ),
            },
            [
                Result(state=State.OK, summary="[0]"),
                Result(state=State.OK, summary="(up)", details="Operational state: up"),
                Result(state=State.OK, summary="Speed: unknown"),
            ],
            id="Missing metrics due to max recursion depth reached",
        ),
    ],
)
def test_check_azure_vm_network_io(
    params: Mapping[str, tuple[float, float]], section: Section, expected_result: CheckResult
) -> None:
    assert list(check_azure_vm_network_io("Network IO", params, section)) == expected_result


def test_check_azure_vm_network_io_error() -> None:
    with pytest.raises(IgnoreResultsError, match="nly one resource expected"):
        list(check_azure_vm_network_io("Network IO", {}, MULTIPLE_VMS_SECTION))
