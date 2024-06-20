#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    RuleSetType,
    Service,
    State,
)
from cmk.plugins.lib.cmciii import (
    discovery_default_parameters,
    DiscoveryParams,
    get_item,
    get_sensor,
    Section,
    Sensor,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict


def discover_cmciii_temp(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    for id_, entry in section["temp"].items():
        # TODO: Should we not handle the dew points somewhere else?
        # In any case, the "Setup" entries contain setpoints and
        # cannot report a temperature to the user.
        if "Value" in entry:
            yield Service(item=get_item(id_, params, entry), parameters={"_item_key": id_})


def _device_levels(entry: Sensor, key_warn: str, key_crit: str) -> tuple[float, float] | None:
    warn, crit = entry.get(key_warn), entry.get(key_crit)
    if warn and crit:
        return (warn, crit)
    if warn:
        return (warn, warn)
    if crit:
        return (crit, crit)
    return None


def check_cmciii_temp(item: str, params: TempParamDict, section: Section) -> CheckResult:
    # Fields from table 8.3.2 Temperature in "Assembly and operating instructions"
    # for software version V3.07.03.
    entry = get_sensor(item, params, section["temp"])
    if not entry:
        return

    descr = entry.get("DescName", "").replace("Temperature", "")
    if descr and descr not in item:
        yield Result(state=State.OK, summary="[%s]" % descr)

    yield from check_temperature(
        entry["Value"],
        params,
        unique_name="cmciii.temp.%s" % item,
        value_store=get_value_store(),
        dev_levels=_device_levels(entry, "SetPtHighWarning", "SetPtHighAlarm"),
        dev_levels_lower=_device_levels(entry, "SetPtLowWarning", "SetPtLowAlarm"),
        dev_status_name=entry.get("Status"),
    )


check_plugin_cmciii_temp = CheckPlugin(
    name="cmciii_temp",
    sections=["cmciii"],
    service_name="Temperature %s",
    discovery_function=discover_cmciii_temp,
    check_function=check_cmciii_temp,
    discovery_ruleset_name="discovery_cmciii",
    discovery_default_parameters=discovery_default_parameters(),
    discovery_ruleset_type=RuleSetType.MERGED,
    check_default_parameters={},
    check_ruleset_name="temperature",
)
