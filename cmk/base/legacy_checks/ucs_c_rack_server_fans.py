#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# exemplary agent output (separator is <TAB> and is tabulator):
# <<<ucs_c_rack_server_fans:sep(9)>>>
# equipmentFan<TAB>dn sys/rack-unit-1/fan-module-1-1/fan-1<TAB>id 1<TAB>model <TAB>operability operable


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def parse_ucs_c_rack_server_fans(string_table):
    parsed = {}

    for fan in string_table:
        try:
            key_value_pairs = [kv.split(" ", 1) for kv in fan[1:]]
            fan = (
                key_value_pairs[0][1]
                .replace("sys/", "")
                .replace("rack-unit-", "Rack Unit ")
                .replace("/fan-module-", " Module ")
                .replace("/fan-", " ")
            )
            parsed[fan] = {"operability": key_value_pairs[3][1]}
        except (IndexError, ValueError):
            pass

    return parsed


def check_ucs_c_rack_server_fans(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    operability_to_status_mapping = {
        "unknown": 3,
        "operable": 0,
        "inoperable": 2,
    }
    operability = data["operability"]
    try:
        status = operability_to_status_mapping[operability]
        status_readable = "Operability Status is %s" % operability
    except KeyError:
        status = 3
        status_readable = "Unknown Operability Status: %s" % operability
    yield status, status_readable


def discover_ucs_c_rack_server_fans(section):
    yield from ((item, {}) for item in section)


check_info["ucs_c_rack_server_fans"] = LegacyCheckDefinition(
    name="ucs_c_rack_server_fans",
    parse_function=parse_ucs_c_rack_server_fans,
    service_name="Fan %s",
    discovery_function=discover_ucs_c_rack_server_fans,
    check_function=check_ucs_c_rack_server_fans,
)
