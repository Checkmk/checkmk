#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<netapp_api_vs_status:sep(9)>>>
# zcs1v    running
# zhs01    running
# zmppl01  running
# zmdp     running
# cdefs1v  running


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def parse_netapp_api_vs_status(string_table):
    parsed = {}
    for line in string_table:
        if len(line) == 2:
            # pre v1.6.0 agent output
            name, state = line
            parsed[name] = {"state": state}
        else:
            parsed[line[0]] = dict(zip(line[1::2], line[2::2]))
    return parsed


def discover_netapp_api_vs_status(section):
    yield from ((item, {}) for item, data in section.items() if "state" in data)


def check_netapp_api_vs_status(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    server_state = data.get("state")
    if not server_state:
        return
    subtype = data.get("vserver-subtype")
    if server_state == "running":
        state = 0
    elif server_state == "stopped" and subtype == "dp_destination":
        state = 0
    else:
        state = 2
    yield state, "State: %s" % server_state
    if subtype:
        yield 0, "Subtype: %s" % subtype


check_info["netapp_api_vs_status"] = LegacyCheckDefinition(
    parse_function=parse_netapp_api_vs_status,
    service_name="vServer Status %s",
    discovery_function=discover_netapp_api_vs_status,
    check_function=check_netapp_api_vs_status,
)
