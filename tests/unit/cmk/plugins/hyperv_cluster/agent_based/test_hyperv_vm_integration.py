#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.hyperv_cluster.agent_based.hyperv_vm_integration import (
    check_hyperv_vm_integration,
    discovery_hyperv_vm_integration,
    hyperv_vm_integration_default_levels,
    Params,
    Section,
)

# Example output from agent:
# <<<hyperv_vm_integration:cached(1750083965,120)>>>
# guest.tools.number 6
# guest.tools.service.Guest_Service_Interface inactive
# guest.tools.service.Heartbeat active
# guest.tools.service.Key-Value_Pair_Exchange active
# guest.tools.service.Shutdown active
# guest.tools.service.Time_Synchronization active
# guest.tools.service.VSS active


def test_check_hyperv_vm_integration_data() -> None:
    sample_section = {
        "guest.tools.number": "6",
        "guest.tools.service.Guest_Service_Interface": "inactive",
        "guest.tools.service.Heartbeat": "active",
        "guest.tools.service.Key-Value_Pair_Exchange": "active",
        "guest.tools.service.Shutdown": "active",
        "guest.tools.service.Time_Synchronization": "active",
        "guest.tools.service.VSS": "active",
    }

    expected_results = [
        Result(state=State.OK, summary="Guest Service Interface - inactive"),
        Result(state=State.OK, summary="Heartbeat - active"),
        Result(state=State.OK, summary="Key-Value Pair Exchange - active"),
        Result(state=State.OK, summary="Shutdown - active"),
        Result(state=State.OK, summary="Time Synchronization - active"),
        Result(state=State.OK, summary="VSS - active"),
    ]

    results = list(
        check_hyperv_vm_integration(hyperv_vm_integration_default_levels, sample_section)
    )
    assert results == expected_results


@pytest.mark.parametrize(
    ["section", "expected"],
    [
        (
            {"guest.tools.number": "6"},
            [Service()],
        ),
        (
            {"guest.tools.service.Heartbeat": "active"},
            [],
        ),
    ],
)
def test_discovery_hyperv_vm_integration(section, expected):
    discovered = list(discovery_hyperv_vm_integration(section))
    assert discovered == expected


@pytest.mark.parametrize(
    ["params", "section", "expected_results"],
    [
        (
            {
                "match_services": [
                    {"service_name": "Guest Service Interface", "expected_state": "inactive"}
                ]
            },
            {
                "guest.tools.service.Guest_Service_Interface": "inactive",
            },
            [
                Result(state=State.OK, summary="Guest Service Interface - inactive"),
            ],
        ),
        (
            {
                "match_services": [
                    {"service_name": "Guest Service Interface", "expected_state": "active"}
                ]
            },
            {
                "guest.tools.service.Heartbeat": "running",
            },
            [
                Result(state=State.UNKNOWN, summary="Heartbeat - running"),
            ],
        ),
        (
            {"match_services": []},
            {
                "guest.tools.service.Guest_Service_Interface": "stopped",
                "guest.tools.service.Heartbeat": "running",
            },
            [
                Result(state=State.UNKNOWN, summary="Guest Service Interface - stopped"),
                Result(state=State.UNKNOWN, summary="Heartbeat - running"),
            ],
        ),
        (
            {
                "match_services": [
                    {"service_name": "Guest Service Interface", "expected_state": "inactive"}
                ]
            },
            {
                "guest.tools.service.Guest_Service_Interface": "active",
            },
            [
                Result(state=State.WARN, summary="Guest Service Interface - active"),
            ],
        ),
    ],
)
def test_check_hyperv_vm_integration(
    params: Params, section: Section, expected_results: list[Result]
) -> None:
    results = list(check_hyperv_vm_integration(params, section))
    assert results == expected_results
