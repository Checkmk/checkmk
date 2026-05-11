#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ibm.lib_svc import parse_ibm_svc_with_header
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# Example output from agent:
# <<<ibm_svc_enclosurestats:sep(58)>>>
# 1:power_w:207:218:140410113051
# 1:temp_c:22:22:140410113246
# 1:temp_f:71:71:140410113246
# 2:power_w:126:128:140410113056
# 2:temp_c:21:21:140410113246
# 2:temp_f:69:69:140410113246
# 3:power_w:123:126:140410113041
# 3:temp_c:22:22:140410113246
# 3:temp_f:71:71:140410113246
# 4:power_w:133:138:140410112821
# 4:temp_c:22:23:140410112836
# 4:temp_f:71:73:140410112836

Section = Mapping[str, Mapping[str, int]]


def parse_ibm_svc_enclosurestats(
    string_table: StringTable,
) -> Section:
    dflt_header = [
        "enclosure_id",
        "stat_name",
        "stat_current",
        "stat_peak",
        "stat_peak_time",
    ]
    parsed: dict[str, dict[str, int]] = {}
    for id_, rows in parse_ibm_svc_with_header(string_table, dflt_header).items():
        for data in rows:
            try:
                stat_current = int(data["stat_current"])
            except ValueError:
                continue
            parsed.setdefault(id_, {}).setdefault(data["stat_name"], stat_current)
    return parsed


agent_section_ibm_svc_enclosurestats = AgentSection(
    name="ibm_svc_enclosurestats",
    parse_function=parse_ibm_svc_enclosurestats,
)

#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def discover_ibm_svc_enclosurestats_temp(section: Section) -> DiscoveryResult:
    for enclosure_id, data in section.items():
        if "temp_c" in data:
            yield Service(item=enclosure_id)


def _check_ibm_svc_enclosurestats_temp(
    item: str,
    params: TempParamType,
    section: Section,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    data = section.get(item)
    if data is None:
        return
    yield from check_temperature(
        data["temp_c"],
        params,
        unique_name=f"ibm_svc_enclosurestats_{item}",
        value_store=value_store,
    )


def check_ibm_svc_enclosurestats_temp(
    item: str, params: TempParamType, section: Section
) -> CheckResult:
    yield from _check_ibm_svc_enclosurestats_temp(item, params, section, get_value_store())


check_plugin_ibm_svc_enclosurestats_temp = CheckPlugin(
    name="ibm_svc_enclosurestats_temp",
    service_name="Temperature Enclosure %s",
    sections=["ibm_svc_enclosurestats"],
    discovery_function=discover_ibm_svc_enclosurestats_temp,
    check_function=check_ibm_svc_enclosurestats_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)

# .
#   .--power---------------------------------------------------------------.
#   |                                                                      |
#   |                    _ __   _____      _____ _ __                      |
#   |                   | '_ \ / _ \ \ /\ / / _ \ '__|                     |
#   |                   | |_) | (_) \ V  V /  __/ |                        |
#   |                   | .__/ \___/ \_/\_/ \___|_|                        |
#   |                   |_|                                                |
#   '----------------------------------------------------------------------'


def discover_ibm_svc_enclosurestats_power(section: Section) -> DiscoveryResult:
    for enclosure_id, data in section.items():
        if "power_w" in data:
            yield Service(item=enclosure_id)


def check_ibm_svc_enclosurestats_power(item: str, section: Section) -> CheckResult:
    data = section.get(item)
    if data is None:
        return
    stat_current = data["power_w"]
    yield Result(state=State.OK, summary=f"{stat_current} Watt")
    yield Metric("power", stat_current)


check_plugin_ibm_svc_enclosurestats_power = CheckPlugin(
    name="ibm_svc_enclosurestats_power",
    service_name="Power Enclosure %s",
    sections=["ibm_svc_enclosurestats"],
    discovery_function=discover_ibm_svc_enclosurestats_power,
    check_function=check_ibm_svc_enclosurestats_power,
)
