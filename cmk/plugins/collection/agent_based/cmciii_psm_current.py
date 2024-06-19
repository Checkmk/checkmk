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


def discover_cmciii_psm_current(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    yield from discover_cmciii_sensors("psm_current", params, section)


def check_cmciii_psm_current(item: str, params: CheckParams, section: Section) -> CheckResult:
    entry = get_sensor(item, params, section["psm_current"])
    if not entry:
        return

    current = entry["Value"]
    min_current = entry["SetPtHighAlarm"]
    max_current = entry["SetPtLowAlarm"]
    state = State.OK if entry["Status"] == "OK" else State.CRIT
    yield Result(state=state, summary=f"Current: {current} ({min_current}/{max_current}), ")
    yield Metric("current", current, levels=(min_current, max_current))

    yield Result(state=State.OK, summary="Type: %s" % entry["Unit Type"])
    yield Result(state=State.OK, summary="Serial: %s" % entry["Serial Number"])
    yield Result(state=State.OK, summary="Position: %s" % entry["Mounting Position"])


check_plugin_cmciii_psm_current = CheckPlugin(
    name="cmciii_psm_current",
    sections=["cmciii"],
    service_name="Current %s",
    discovery_function=discover_cmciii_psm_current,
    check_function=check_cmciii_psm_current,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=RuleSetType.MERGED,
    check_default_parameters={},
)
