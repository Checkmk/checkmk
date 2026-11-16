#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.hwg.agent_based.lib import READABLE_STATES, SectionHwg


def discover_hwg_sensor(section: SectionHwg) -> DiscoveryResult:
    for index, attrs in section.items():
        if "value" in attrs and attrs["dev_status_name"] not in ["invalid", ""]:
            yield Service(item=index)


def check_hwg_sensor(
    item: str, params: Mapping[str, tuple[float, float]], section: SectionHwg
) -> CheckResult:
    if not (data := section.get(item)) or "value" not in data:
        return

    if (value := data["value"]) is None:
        yield Result(state=State.UNKNOWN, summary="Value: not readable")
    else:
        yield from check_levels(
            value,
            levels_upper=("fixed", upper) if (upper := params.get("levels")) else None,
            levels_lower=("fixed", lower) if (lower := params.get("levels_lower")) else None,
            metric_name="generic_number",
            label="Value",
        )
    yield Result(state=State.OK, summary=f"Description: {data['descr']}")
    yield Result(
        state=READABLE_STATES.get(data["dev_status_name"], State.UNKNOWN),
        summary=f"Status: {data['dev_status_name']}",
    )


check_plugin_hwg_sensor = CheckPlugin(
    name="hwg_sensor",
    service_name="Sensor %s",
    sections=["hwg_temp"],
    discovery_function=discover_hwg_sensor,
    check_function=check_hwg_sensor,
    check_ruleset_name="generic_number",
    check_default_parameters={},
)


check_plugin_hwg_ste2_sensor = CheckPlugin(
    name="hwg_ste2_sensor",
    service_name="Sensor %s",
    sections=["hwg_ste2"],
    discovery_function=discover_hwg_sensor,
    check_function=check_hwg_sensor,
    check_ruleset_name="generic_number",
    check_default_parameters={},
)
