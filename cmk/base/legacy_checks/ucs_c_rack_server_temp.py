#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# exemplary output of special agent agent_ucs_bladecenter (<TAB> is tabulator):
#
# <<<ucsc_server_temp:sep(9)>>>
# processorEnvStats<TAB>dn sys/rack-unit-1/board/cpu-1/env-stats<TAB>id 1<TAB>description blalub<TAB>temperature 58.4
# processorEnvStats<TAB>dn sys/rack-unit-1/board/cpu-2/env-stats<TAB>id 2<TAB>description blalub<TAB>temperature 50.4
# memoryUnitEnvStats<TAB>dn sys/rack-unit-1/board/memarray-1/mem-1/dimm-env-stats<TAB>id 1<TAB>description blalub<TAB>temperature 40.4
# memoryUnitEnvStats<TAB>dn sys/rack-unit-1/board/memarray-1/mem-2/dimm-env-stats<TAB>id 2<TAB>description blalub<TAB>temperature 41.4
# computeRackUnitMbTempStats<TAB>dn sys/rack-unit-1/board/temp-stats<TAB>ambientTemp 50.0<TAB>frontTemp 50.0<TAB>ioh1Temp 50.0<TAB>ioh2Temp 50.0<TAB>rearTemp 50.0
# computeRackUnitMbTempStats<TAB>dn sys/rack-unit-2/board/temp-stats<TAB>ambientTemp 50.0<TAB>frontTemp 50.0<TAB>ioh1Temp 50.0<TAB>ioh2Temp 50.0<TAB>rearTemp 50.0


def parse_ucs_c_rack_server_temp(string_table):
    """
    Returns dict with indexed processors, memory units and motherboards mapped to keys and
    temperature as value.
    """
    parsed = {}
    for line in string_table:
        key_value_pairs = [kv.split(" ", 1) for kv in line[1:]]
        if "cpu-" in key_value_pairs[0][1]:
            cpu = (
                key_value_pairs[0][1]
                .replace("sys/", "")
                .replace("rack-unit-", "Rack Unit ")
                .replace("/board", "")
                .replace("/cpu-", " CPU ")
                .replace("/env-stats", "")
            )
            try:
                parsed[cpu] = float(key_value_pairs[3][1])
            except (ValueError, KeyError):
                continue  # skip potentially invalid agent output
        elif "mem-" in key_value_pairs[0][1]:
            mem = (
                key_value_pairs[0][1]
                .replace("sys/", "")
                .replace("rack-unit-", "Rack Unit ")
                .replace("/board", "")
                .replace("/memarray-", " Memory Array ")
                .replace("/mem-", " Memory DIMM ")
                .replace("/dimm-env-stats", "")
            )
            try:
                parsed[mem] = float(key_value_pairs[3][1])
            except (ValueError, KeyError):
                continue  # skip potentially invalid agent output
        elif "board" in key_value_pairs[0][1]:
            mb = (
                key_value_pairs[0][1]
                .replace("sys/", "")
                .replace("rack-unit-", "Rack Unit ")
                .replace("/board/temp-stats", " Motherboard")
            )
            try:
                parsed[mb] = float(key_value_pairs[2][1])
            except (ValueError, KeyError):
                continue  # skip potentially invalid agent output
        else:
            continue  # skip potentially invalid agent output
    return parsed


def check_ucs_c_rack_server_temp(item, params, parsed):
    if (temperature := parsed.get(item)) is None:
        return
    yield check_temperature(
        temperature, params, "ucs_c_rack_server_%s" % item.lower().replace(" ", "_")
    )


def discover_ucs_c_rack_server_temp(section):
    yield from ((item, {}) for item in section)


check_info["ucs_c_rack_server_temp"] = LegacyCheckDefinition(
    name="ucs_c_rack_server_temp",
    parse_function=parse_ucs_c_rack_server_temp,
    service_name="Temperature %s",
    discovery_function=discover_ucs_c_rack_server_temp,
    check_function=check_ucs_c_rack_server_temp,
    check_ruleset_name="temperature",
)
