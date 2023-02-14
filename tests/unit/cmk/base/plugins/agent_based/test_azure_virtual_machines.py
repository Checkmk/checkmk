#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from tests.unit.conftest import FixRegister

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.azure_virtual_machine import (
    _MAP_POWER,
    _MAP_PROVISIONING,
    check_azure_virtual_machine,
    check_azure_virtual_machine_summary,
    discover_azure_virtual_machine,
    discover_azure_virtual_machine_summary,
    VMSummaryParams,
)
from cmk.base.plugins.agent_based.utils.azure import Resource, Section

DEFAULT_PARAMS = {
    "map_provisioning_states": _MAP_PROVISIONING,
    "map_power_states": _MAP_POWER,
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
            DEFAULT_PARAMS,
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
            },
            [
                Result(state=State.OK, summary="Provisioning succeeded"),
                Result(state=State.OK, summary="VM running"),
                Result(state=State.OK, summary="Location: uksouth"),
            ],
            id="statuses present, no message",
        ),
        pytest.param(
            "VM-test-1",
            DEFAULT_PARAMS,
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
            DEFAULT_PARAMS,
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
            DEFAULT_PARAMS,
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
    params: Mapping[str, Mapping[str, int]],
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
    fix_register: FixRegister,
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
