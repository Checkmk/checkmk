#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    RuleSetType,
)
from cmk.plugins.lib.cmciii import (
    discover_cmciii_sensors,
    discovery_default_parameters,
    DiscoveryParams,
    get_sensor,
    Section,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict


def discover_cmciii_temp_in_out(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    yield from discover_cmciii_sensors("temp_in_out", params, section)


def check_cmciii_temp_in_out(item: str, params: TempParamDict, section: Section) -> CheckResult:
    entry = get_sensor(item, params, section["temp_in_out"])
    if not entry:
        return
    yield from check_temperature(
        entry["Value"],
        params,
        unique_name="cmciii.temp_in_out.%s" % item,
        value_store=get_value_store(),
    )


check_plugin_cmciii_temp_in_out = CheckPlugin(
    name="cmciii_temp_in_out",
    sections=["cmciii"],
    service_name="Temperature %s",
    discovery_function=discover_cmciii_temp_in_out,
    check_function=check_cmciii_temp_in_out,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=RuleSetType.MERGED,
    check_default_parameters={},
    check_ruleset_name="temperature",
)
