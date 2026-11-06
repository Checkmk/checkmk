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
from cmk.plugins.prism.agent_based.prism_ha import (
    check_prism_ha,
    discovery_prism_ha,
    parse_prism_ha_v2,
)

SECTION = {
    "failover_enabled": True,
    "failover_in_progress_host_uuids": None,
    "ha_state": "BestEffort",
    "logical_timestamp": 0,
    "num_host_failures_to_tolerate": 0,
    "reservation_type": "NoReservations",
    "reserved_host_uuids": None,
}


@pytest.mark.parametrize(
    ["section", "expected_discovery_result"],
    [
        pytest.param(
            SECTION,
            [
                Service(),
            ],
            id="The service is discovered if data exists.",
        ),
        pytest.param({}, [], id="No services is discovered if no data exists."),
    ],
)
def test_discovery_prism_ha(  # type: ignore[misc]
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_ha(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["section", "expected_check_result"],
    [
        pytest.param(
            SECTION,
            [
                Result(state=State.OK, summary="State: BestEffort"),
            ],
            id="If state is as expected, service is OK.",
        ),
        pytest.param(
            {},
            [],
            id="No data",
        ),
    ],
)
def test_check_prism_ha(  # type: ignore[misc]
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_ha(
                section=section,
            )
        )
        == expected_check_result
    )


# What the v4 agent writes for the cluster recorded on a Prism Central 7.5 lab: its 3 AHV hosts
RECORDED_V4_SECTION = [
    [
        (
            Path(__file__).parent.parent
            / "special_agent"
            / "v4_fixtures"
            / "section_prism_ha_v2.json"
        ).read_text()
    ]
]


def _v4_hosts(*hypervisors: Mapping[str, str]) -> StringTable:
    return [[json.dumps([{"hypervisor": hypervisor} for hypervisor in hypervisors])]]


def _ahv(state: str) -> Mapping[str, str]:
    return {"type": "AHV", "state": state}


def _v4_results(string_table: StringTable) -> list[Result]:
    return [
        result
        for result in check_prism_ha(section=parse_prism_ha_v2(string_table))
        if isinstance(result, Result)
    ]


def test_v4_cluster_with_normal_hosts_is_best_effort() -> None:
    section = parse_prism_ha_v2(RECORDED_V4_SECTION)

    assert (list(discovery_prism_ha(section)), list(check_prism_ha(section=section))) == (
        [Service()],
        [Result(state=State.OK, summary="State: BestEffort")],
    )


@pytest.mark.parametrize(
    ["states", "expected"],
    [
        pytest.param(
            ["ACROPOLIS_NORMAL", "RESERVED_FOR_HA_FAILOVER"],
            Result(state=State.OK, summary="State: HighlyAvailable"),
            id="reserved host",
        ),
        pytest.param(
            ["ACROPOLIS_NORMAL", "RESERVING_FOR_HA_FAILOVER"],
            Result(state=State.OK, summary="State: BestEffort"),
            id="host being reserved",
        ),
        pytest.param(
            ["RESERVED_FOR_HA_FAILOVER", "HA_FAILOVER_TARGET"],
            Result(state=State.WARN, summary="State: Healing"),
            id="failover beats a reservation",
        ),
        pytest.param(
            ["ACROPOLIS_NORMAL", "HA_HEALING_SOURCE"],
            Result(state=State.WARN, summary="State: Healing"),
            id="healing",
        ),
        pytest.param(
            ["ACROPOLIS_NORMAL", "ENTERING_MAINTENANCE_MODE_FROM_HA_FAILOVER"],
            Result(state=State.WARN, summary="State: Healing"),
            id="maintenance after a failover",
        ),
        pytest.param(
            ["ACROPOLIS_NORMAL", "ENTERED_MAINTENANCE_MODE"],
            Result(state=State.OK, summary="State: BestEffort"),
            id="maintenance mode",
        ),
        pytest.param(
            ["$UNKNOWN", "HA_HEALING_TARGET"],
            Result(state=State.WARN, summary="State: Healing"),
            id="an unknown state is ignored",
        ),
        pytest.param(
            ["$UNKNOWN", "$REDACTED"],
            Result(state=State.UNKNOWN, summary="State: Unknown"),
            id="no known state",
        ),
    ],
)
def test_v4_ha_state_follows_the_host_states(states: Sequence[str], expected: Result) -> None:
    assert _v4_results(_v4_hosts(*(_ahv(state) for state in states))) == [expected]


def test_v4_host_without_a_state_is_ignored() -> None:
    assert _v4_results(_v4_hosts({"type": "AHV"}, _ahv("HA_FAILOVER_SOURCE"))) == [
        Result(state=State.WARN, summary="State: Healing")
    ]


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param(
            _v4_hosts(_ahv("ACROPOLIS_NORMAL"), {"type": "ESX", "state": "ACROPOLIS_NORMAL"}),
            id="mixed hypervisors",
        ),
        pytest.param(_v4_hosts({"type": "ESX", "state": "ACROPOLIS_NORMAL"}), id="ESXi only"),
        pytest.param(_v4_hosts(), id="no hosts"),
        pytest.param([], id="empty section"),
    ],
)
def test_v4_cluster_that_is_not_only_ahv_has_no_service(string_table: StringTable) -> None:
    assert list(discovery_prism_ha(parse_prism_ha_v2(string_table))) == []
