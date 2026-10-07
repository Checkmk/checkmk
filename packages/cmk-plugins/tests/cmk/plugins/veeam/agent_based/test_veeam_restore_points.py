#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
import time_machine

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.veeam.agent_based.veeam_restore_points import (
    check_veeam_restore_points,
    CheckParameters,
    discovery_veeam_restore_points,
    parse_veeam_restore_points,
)

PARAMS = CheckParameters(age=("fixed", (30 * 3600.0, 48 * 3600.0)))

ITEM = "VMware - vm-1"

LAST_CREATION_TIME = "2026-10-01T00:00:00+00:00"


def _object(name: str = "vm-1", **overrides: object) -> list[str]:
    object_dict: dict[str, object] = {
        "id": "id-1",
        "name": name,
        "platformName": "VMware",
        "type": "VM",
        "restorePointsCount": 3,
        "lastRestorePoint": {
            "creationTime": LAST_CREATION_TIME,
            "type": "Increment",
            "malwareStatus": "Clean",
        },
        "malwareStatus": "Clean",
    }
    object_dict.update(overrides)
    return [json.dumps(object_dict)]


def _states(item: str, string_table: list[list[str]]) -> list[State]:
    section = parse_veeam_restore_points(string_table)
    return [
        r.state for r in check_veeam_restore_points(item, PARAMS, section) if isinstance(r, Result)
    ]


def test_discovery_veeam_restore_points() -> None:
    section = parse_veeam_restore_points([_object("vm-1"), _object("vm-2")])
    assert list(discovery_veeam_restore_points(section)) == [
        Service(item="VMware - vm-1"),
        Service(item="VMware - vm-2"),
    ]


def test_discovery_veeam_restore_points_same_name_on_two_platforms() -> None:
    section = parse_veeam_restore_points([_object("vm-1"), _object("vm-1", platformName="HyperV")])
    assert list(discovery_veeam_restore_points(section)) == [
        Service(item="VMware - vm-1"),
        Service(item="HyperV - vm-1"),
    ]


@time_machine.travel("2026-10-01T02:00:00+00:00", tick=False)
def test_check_veeam_restore_points_summary_and_details() -> None:
    section = parse_veeam_restore_points([_object()])
    assert list(check_veeam_restore_points(ITEM, PARAMS, section)) == [
        Result(state=State.OK, summary="3 restore points"),
        Result(state=State.OK, summary="last: 2 hours 0 minutes ago"),
        Result(state=State.OK, notice="Malware status: Clean"),
        Result(state=State.OK, notice="Platform: VMware"),
        Result(state=State.OK, notice="Object type: VM"),
        Result(state=State.OK, notice="Last restore point type: Increment"),
        Result(state=State.OK, notice="Last restore point malware status: Clean"),
    ]


@pytest.mark.parametrize(
    "now, expected",
    [
        pytest.param("2026-10-02T05:59:00+00:00", State.OK, id="just below warn"),
        pytest.param("2026-10-02T06:00:00+00:00", State.WARN, id="warn at 30 h"),
        pytest.param("2026-10-03T00:00:00+00:00", State.CRIT, id="crit at 48 h"),
    ],
)
def test_check_veeam_restore_points_age_levels(now: str, expected: State) -> None:
    with time_machine.travel(now, tick=False):
        assert State.worst(*_states(ITEM, [_object()])) == expected


@time_machine.travel("2026-10-01T02:00:00+00:00", tick=False)
@pytest.mark.parametrize(
    "malware_status, expected",
    [
        pytest.param("Clean", State.OK, id="clean"),
        pytest.param("Informative", State.OK, id="informative"),
        pytest.param("Suspicious", State.WARN, id="suspicious"),
        pytest.param("Infected", State.CRIT, id="infected"),
        pytest.param("SomethingNew", State.UNKNOWN, id="unknown value"),
        pytest.param(None, State.OK, id="not scanned"),
    ],
)
def test_check_veeam_restore_points_malware_status(
    malware_status: str | None, expected: State
) -> None:
    assert State.worst(*_states(ITEM, [_object(malwareStatus=malware_status)])) == expected


def test_check_veeam_restore_points_zero_restore_points_is_crit() -> None:
    section = parse_veeam_restore_points(
        [_object(restorePointsCount=0, lastRestorePoint=None, malwareStatus=None)]
    )
    results = list(check_veeam_restore_points(ITEM, PARAMS, section))
    assert results[0] == Result(state=State.CRIT, summary="0 restore points")
    assert State.worst(*(r.state for r in results if isinstance(r, Result))) == State.CRIT


def test_check_veeam_restore_points_newest_not_found_is_unknown() -> None:
    section = parse_veeam_restore_points([_object(lastRestorePoint=None, malwareStatus=None)])
    assert Result(
        state=State.UNKNOWN, summary="Newest restore point not found"
    ) in check_veeam_restore_points(ITEM, PARAMS, section)


@time_machine.travel("2026-09-30T00:00:00+00:00", tick=False)
def test_check_veeam_restore_points_in_the_future() -> None:
    section = parse_veeam_restore_points([_object()])
    assert Result(
        state=State.OK, summary="Last restore point is in the future"
    ) in check_veeam_restore_points(ITEM, PARAMS, section)


def test_check_veeam_restore_points_unknown_count_is_unknown() -> None:
    section = parse_veeam_restore_points([_object(restorePointsCount=None)])
    assert next(iter(check_veeam_restore_points(ITEM, PARAMS, section))) == Result(
        state=State.UNKNOWN, summary="Number of restore points unknown"
    )


@time_machine.travel("2026-10-01T02:00:00+00:00", tick=False)
def test_check_veeam_restore_points_missing_fields_do_not_crash() -> None:
    section = parse_veeam_restore_points(
        [
            _object(
                platformName=None,
                type=None,
                lastRestorePoint={"creationTime": None, "type": None, "malwareStatus": None},
            )
        ]
    )
    results = list(check_veeam_restore_points("vm-1", PARAMS, section))
    assert Result(state=State.UNKNOWN, summary="Newest restore point not found") in results
    assert Result(state=State.OK, notice="Last restore point type: unknown") in results


def test_check_veeam_restore_points_missing_item() -> None:
    section = parse_veeam_restore_points([_object()])
    assert not list(check_veeam_restore_points("VMware - vm-2", PARAMS, section))
