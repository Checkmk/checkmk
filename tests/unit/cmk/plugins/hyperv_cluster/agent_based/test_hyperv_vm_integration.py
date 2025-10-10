#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.hyperv_cluster.agent_based.hyperv_vm_integration import (
    check_hyperv_vm_integration,
    discovery_hyperv_vm_integration,
    hyperv_vm_integration_default_levels,
    IntegrationServicesParams,
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
    sample_section: Section = {
        "guest.tools.number": "6",
        "guest.tools.service.Guest_Service_Interface": "inactive",
        "guest.tools.service.Heartbeat": "active",
        "guest.tools.service.Key-Value_Pair_Exchange": "active",
        "guest.tools.service.Shutdown": "active",
        "guest.tools.service.Time_Synchronization": "active",
        "guest.tools.service.VSS": "active",
    }

    expected_results = [
        Result(state=State.OK, summary="Guest Service Interface: inactive"),
        Result(state=State.OK, summary="Heartbeat: active"),
        Result(state=State.OK, summary="Key-Value Pair Exchange: active"),
        Result(state=State.OK, summary="Shutdown: active"),
        Result(state=State.OK, summary="Time Synchronization: active"),
        Result(state=State.OK, summary="VSS (Volume Shadow Copy Service): active"),
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
                "default_status": "active",
                "state_if_not_default": State.WARN.value,
                "match_services": [],
            },
            {
                "guest.tools.service.Heartbeat": "active",
            },
            [
                Result(state=State.OK, summary="Heartbeat: active"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.WARN.value,
                "match_services": [],
            },
            {
                "guest.tools.service.Heartbeat": "inactive",
            },
            [
                Result(state=State.WARN, summary="Heartbeat: inactive"),
            ],
        ),
        (
            {
                "default_status": "inactive",
                "state_if_not_default": State.CRIT.value,
                "match_services": [],
            },
            {
                "guest.tools.service.Time_Synchronization": "inactive",
            },
            [
                Result(state=State.OK, summary="Time Synchronization: inactive"),
            ],
        ),
        (
            {
                "default_status": "inactive",
                "state_if_not_default": State.CRIT.value,
                "match_services": [],
            },
            {
                "guest.tools.service.Time_Synchronization": "active",
            },
            [
                Result(state=State.CRIT, summary="Time Synchronization: active"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.OK.value,
                "match_services": [],
            },
            {
                "guest.tools.service.VSS": "inactive",
            },
            [
                Result(state=State.OK, summary="VSS (Volume Shadow Copy Service): inactive"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.UNKNOWN.value,
                "match_services": [],
            },
            {
                "guest.tools.service.Shutdown": "invalid_status",
            },
            [
                Result(state=State.UNKNOWN, summary="Shutdown: invalid_status"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.WARN.value,
                "match_services": [
                    {
                        "service_name": "Guest Service Interface",
                        "default_status": "inactive",
                        "state_if_not_default": State.OK.value,
                    }
                ],
            },
            {
                "guest.tools.service.Guest_Service_Interface": "active",
                "guest.tools.service.Heartbeat": "inactive",
                "guest.tools.service.Time_Synchronization": "active",
            },
            [
                Result(state=State.OK, summary="Guest Service Interface: active"),
                Result(state=State.WARN, summary="Heartbeat: inactive"),
                Result(state=State.OK, summary="Time Synchronization: active"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.CRIT.value,
                "match_services": [],
            },
            {
                "guest.tools.service.Heartbeat": "inactive",
                "guest.tools.service.Shutdown": "inactive",
                "guest.tools.service.VSS": "active",
            },
            [
                Result(state=State.CRIT, summary="Heartbeat: inactive"),
                Result(state=State.CRIT, summary="Shutdown: inactive"),
                Result(state=State.OK, summary="VSS (Volume Shadow Copy Service): active"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.WARN.value,
                "match_services": [
                    {
                        "service_name": "Guest Service Interface",
                        "default_status": "inactive",
                        "state_if_not_default": State.OK.value,
                    }
                ],
            },
            {
                "guest.tools.service.Guest_Service_Interface": "inactive",
            },
            [
                Result(state=State.OK, summary="Guest Service Interface: inactive"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.WARN.value,
                "match_services": [
                    {
                        "service_name": "Guest Service Interface",
                        "default_status": "active",
                        "state_if_not_default": State.WARN.value,
                    }
                ],
            },
            {
                "guest.tools.service.Heartbeat": "running",
            },
            [
                Result(state=State.UNKNOWN, summary="Heartbeat: running"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.WARN.value,
                "match_services": [],
            },
            {
                "guest.tools.service.Guest_Service_Interface": "stopped",
                "guest.tools.service.Heartbeat": "running",
            },
            [
                Result(state=State.UNKNOWN, summary="Guest Service Interface: stopped"),
                Result(state=State.UNKNOWN, summary="Heartbeat: running"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.WARN.value,
                "match_services": [
                    {
                        "service_name": "Guest Service Interface",
                        "default_status": "inactive",
                        "state_if_not_default": State.OK.value,
                    }
                ],
            },
            {
                "guest.tools.service.Guest_Service_Interface": "active",
            },
            [
                Result(state=State.OK, summary="Guest Service Interface: active"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.WARN.value,
                "match_services": [
                    {
                        "service_name": "Guest Service Interface",
                        "default_status": "inactive",
                        "state_if_not_default": State.OK.value,
                    }
                ],
            },
            {
                "guest.tools.service.Guest_Service_Interface": "active",
            },
            [
                Result(state=State.OK, summary="Guest Service Interface: active"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.WARN.value,
                "match_services": [
                    {
                        "service_name": "Heartbeat",
                        "default_status": "active",
                        "state_if_not_default": State.CRIT.value,
                    }
                ],
            },
            {
                "guest.tools.service.Heartbeat": "inactive",
            },
            [
                Result(state=State.CRIT, summary="Heartbeat: inactive"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.WARN.value,
                "match_services": [
                    {
                        "service_name": "Time Synchronization",
                        "default_status": "active",
                        "state_if_not_default": State.WARN.value,
                    }
                ],
            },
            {
                "guest.tools.service.Time_Synchronization": "invalid_status",
            },
            [
                Result(state=State.UNKNOWN, summary="Time Synchronization: invalid_status"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.WARN.value,
                "match_services": [
                    {
                        "service_name": "VSS",
                        "default_status": "active",
                        "state_if_not_default": State.WARN.value,
                    }
                ],
            },
            {
                "guest.tools.service.VSS": "inactive",
            },
            [
                Result(state=State.WARN, summary="VSS (Volume Shadow Copy Service): inactive"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.WARN.value,
                "match_services": [
                    {
                        "service_name": "Guest Service Interface",
                        "default_status": "inactive",
                        "state_if_not_default": State.OK.value,
                    },
                    {
                        "service_name": "Heartbeat",
                        "default_status": "active",
                        "state_if_not_default": State.CRIT.value,
                    },
                ],
            },
            {
                "guest.tools.service.Guest_Service_Interface": "active",
                "guest.tools.service.Heartbeat": "inactive",
            },
            [
                Result(state=State.OK, summary="Guest Service Interface: active"),
                Result(state=State.CRIT, summary="Heartbeat: inactive"),
            ],
        ),
        (
            {
                "default_status": "active",
                "state_if_not_default": State.WARN.value,
                "match_services": [],
            },
            {
                "guest.tools.service.Guest_Service_Interface": "inactive",
            },
            [
                Result(state=State.OK, summary="Guest Service Interface: inactive"),
            ],
        ),
    ],
)
def test_check_hyperv_vm_integration(
    params: IntegrationServicesParams, section: Section, expected_results: list[Result]
) -> None:
    results = list(check_hyperv_vm_integration(params, section))
    assert results == expected_results
