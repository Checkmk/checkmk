#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    RuleSetType,
    State,
)
from cmk.plugins.lib.cmciii import (
    CheckParams,
    discover_cmciii_sensors,
    discovery_default_parameters,
    DiscoveryParams,
    get_sensor,
    Section,
)


def discover_cmciii_can_current(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    yield from discover_cmciii_sensors("can_current", params, section)


def check_cmciii_can_current(item: str, params: CheckParams, section: Section) -> CheckResult:
    entry = get_sensor(item, params, section["can_current"])
    if not entry:
        return

    state_readable = entry["Status"]
    value = entry["Value"]
    warn = entry["SetPtHighWarning"]
    crit = entry["SetPtHighAlarm"]

    state = State.OK if state_readable == "OK" else State.CRIT
    yield Result(
        state=state,
        summary=f"Status: {state_readable}, Current: {value} mA (warn/crit at {warn}/{crit} mA)",
    )
    yield Metric("current", value / 1000.0, levels=(warn / 1000.0, crit / 1000.0))


check_plugin_cmciii_can_current = CheckPlugin(
    name="cmciii_can_current",
    sections=["cmciii"],
    service_name="%s",
    discovery_function=discover_cmciii_can_current,
    check_function=check_cmciii_can_current,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=RuleSetType.MERGED,
    check_default_parameters={},
)
