#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any

from cmk.agent_based.v2 import Metric, Result, StringTable
from cmk.plugins.redfish.agent_based.redfish_environmentmetrics import (
    check_redfish_environmentmetrics,
    discovery_redfish_environmentmetrics,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple


def _make_environmentmetrics(
    metrics_id: str = "EnvironmentMetrics",
    *,
    power_watts: float | None = 421.0,
    fan_speeds: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "@odata.id": "/redfish/v1/Chassis/System.Embedded.1/EnvironmentMetrics",
        "@odata.type": "#EnvironmentMetrics.v1_3_0.EnvironmentMetrics",
        "Id": metrics_id,
        "Name": "EnvironmentMetrics",
    }
    if power_watts is not None:
        entry["PowerWatts"] = {"Reading": power_watts}
    entry["FanSpeedsPercent"] = fan_speeds or []
    return entry


def _make_string_table(*entries: dict[str, Any]) -> StringTable:
    return [[json.dumps(e)] for e in entries]


def test_discovery() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_environmentmetrics()))
    services = list(discovery_redfish_environmentmetrics(parsed))
    assert len(services) == 1


def test_check_power_consumption() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_environmentmetrics(power_watts=421.0)))
    item = next(iter(parsed))
    results = list(check_redfish_environmentmetrics(item, parsed))

    result_items = [r for r in results if isinstance(r, Result)]
    metric_items = [r for r in results if isinstance(r, Metric)]

    assert any("421 W" in r.summary for r in result_items if r.summary)
    assert any(m.name == "power" and m.value == 421.0 for m in metric_items)


def test_check_no_power_data() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_environmentmetrics(power_watts=None)))
    item = next(iter(parsed))
    results = list(check_redfish_environmentmetrics(item, parsed))

    metric_items = [r for r in results if isinstance(r, Metric)]
    assert not any(m.name == "power" for m in metric_items)


def test_check_missing_item() -> None:
    parsed = parse_redfish_multiple(_make_string_table(_make_environmentmetrics()))
    results = list(check_redfish_environmentmetrics("nonexistent", parsed))
    assert len(results) == 0
