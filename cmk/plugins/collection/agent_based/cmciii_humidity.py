#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Result, RuleSetType, State
from cmk.plugins.lib.cmciii import (
    CheckParams,
    discover_cmciii_sensors,
    discovery_default_parameters,
    DiscoveryParams,
    get_sensor,
    Section,
)
from cmk.plugins.lib.humidity import check_humidity


def discover_cmciii_humidity(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    yield from discover_cmciii_sensors("humidity", params, section)


def check_cmciii_humidity(item: str, params: CheckParams, section: Section) -> CheckResult:
    entry = get_sensor(item, params, section["humidity"])
    if not entry:
        return

    state_readable = entry["Status"]
    state = State.OK if state_readable == "OK" else State.CRIT
    yield Result(state=state, summary="Status: %s" % state_readable)
    yield from check_humidity(entry["Value"], params)


check_plugin_cmciii_humidity = CheckPlugin(
    name="cmciii_humidity",
    sections=["cmciii"],
    service_name="%s",
    discovery_function=discover_cmciii_humidity,
    check_function=check_cmciii_humidity,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=RuleSetType.MERGED,
    check_default_parameters={},
    check_ruleset_name="humidity",
)
