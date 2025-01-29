#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.9.9.147.1.2.2.2.1.3.40.6  "number of connections currently in use by the entire firewall"
# .1.3.6.1.4.1.9.9.147.1.2.2.2.1.3.40.7  "highest number of connections in use at any one time since system startup"
# .1.3.6.1.4.1.9.9.147.1.2.2.2.1.5.40.6  1045
# .1.3.6.1.4.1.9.9.147.1.2.2.2.1.5.40.7  2816


# mypy: disable-error-code="list-item"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, contains, SNMPTree, startswith, StringTable

check_info = {}


def inventory_cisco_asa_connections(info):
    return [(None, {})]


def check_cisco_asa_connections(_no_item, params, info):
    used_conns = int(info[0][0])
    overall_used_conns = info[1][0]
    infotext = "Currently used: %s" % used_conns
    state = 0

    if params.get("connections"):
        warn, crit = params["connections"]
        perfdata = [("fw_connections_active", used_conns, warn, crit)]
        if used_conns >= crit:
            state = 2
        elif used_conns >= warn:
            state = 1
        if state > 0:
            infotext += f" (warn/crit at {warn}/{crit})"
    else:
        perfdata = [("fw_connections_active", used_conns)]

    return state, f"{infotext}, Max. since system startup: {overall_used_conns}", perfdata


def parse_cisco_asa_connections(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["cisco_asa_connections"] = LegacyCheckDefinition(
    name="cisco_asa_connections",
    parse_function=parse_cisco_asa_connections,
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.1.0", "cisco adaptive security"),
        startswith(".1.3.6.1.2.1.1.1.0", "cisco firewall services"),
        contains(".1.3.6.1.2.1.1.1.0", "cisco pix security"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.147.1.2.2.2.1",
        oids=["5"],
    ),
    service_name="Connections",
    discovery_function=inventory_cisco_asa_connections,
    check_function=check_cisco_asa_connections,
    check_ruleset_name="cisco_fw_connections",
)
