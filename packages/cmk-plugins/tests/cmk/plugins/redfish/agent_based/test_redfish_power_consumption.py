#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_power_consumption import (
    check_redfish_power_consumption,
    discovery_redfish_power_consumption,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple


def _make_power_entry(
    *,
    member_id: str = "0",
    name: str = "PowerControl",
    consumed_watts: int = 421,
    capacity_watts: float | None = 1960.0,
    avg_watts: int | None = 408,
    min_watts: int | None = 384,
    max_watts: int | None = 431,
) -> str:
    power_metrics: dict[str, int] = {}
    if avg_watts is not None:
        power_metrics["AverageConsumedWatts"] = avg_watts
    if min_watts is not None:
        power_metrics["MinConsumedWatts"] = min_watts
    if max_watts is not None:
        power_metrics["MaxConsumedWatts"] = max_watts

    entry: dict[str, Any] = {
        "@odata.id": "/redfish/v1/Chassis/System.Embedded.1/Power",
        "@odata.type": "#Power.v1_7_1.Power",
        "Id": "Power",
        "PowerControl": [
            {
                "MemberId": member_id,
                "Name": name,
                "PowerConsumedWatts": consumed_watts,
                **({"PowerCapacityWatts": capacity_watts} if capacity_watts is not None else {}),
                **({"PowerMetrics": power_metrics} if power_metrics else {}),
            }
        ],
    }
    return json.dumps(entry)


def _make_string_table(*entries: str) -> StringTable:
    return [[e] for e in entries]


def test_discovery_redfish_power_consumption() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_power_entry()))
    services = list(discovery_redfish_power_consumption(parsed))
    assert len(services) == 1
    assert services[0].item is None


def test_check_power_consumption_with_metrics() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_power_entry()))
    results = list(check_redfish_power_consumption(parsed))
    assert (
        Result(
            state=State.OK,
            summary="PowerControl: PowerCapacityWatts - 1960.0 W / PowerConsumedWatts - 421 W",
        )
        in results
    )
    assert Metric("averageconsumedwatts_0", 408.0, boundaries=(0, 1960.0)) in results
    assert Metric("minconsumedwatts_0", 384.0, boundaries=(0, 1960.0)) in results
    assert Metric("maxconsumedwatts_0", 431.0, boundaries=(0, 1960.0)) in results


def test_check_power_consumption_without_capacity() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_power_entry(capacity_watts=None)))
    results = list(check_redfish_power_consumption(parsed))
    metrics = [r for r in results if isinstance(r, Metric)]
    for m in metrics:
        assert m.boundaries == (None, None)


def test_check_power_consumption_no_data() -> None:
    entry = json.dumps(
        {
            "@odata.id": "/redfish/v1/Chassis/System.Embedded.1/Power",
            "@odata.type": "#Power.v1_7_1.Power",
            "Id": "Power",
        }
    )
    parsed = parse_redfish_multiple(_make_string_table(entry))
    results = list(check_redfish_power_consumption(parsed))
    assert results == []
