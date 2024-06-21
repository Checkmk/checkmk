#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.acme import DETECT_ACME


def inventory_acme_realm(info):
    return [
        (name, {}) for name, _inbound, _outbound, _total_inbound, _total_outbound, _state in info
    ]


def check_acme_realm(item, params, info):
    map_states = {
        "3": (0, "in service"),
        "4": (1, "contraints violation"),
        "7": (2, "call load reduction"),
    }
    for name, inbound, outbound, total_inbound, total_outbound, state in info:
        if item == name:
            dev_state, dev_state_readable = map_states[state]
            return (
                dev_state,
                f"Status: {dev_state_readable}, Inbound: {inbound}/{total_inbound}, Outbound: {outbound}/{total_outbound}",
                [
                    ("inbound", int(inbound), None, None, 0, int(total_inbound)),
                    ("outbound", int(outbound), None, None, 0, int(total_outbound)),
                ],
            )
    return None


def parse_acme_realm(string_table: StringTable) -> StringTable:
    return string_table


check_info["acme_realm"] = LegacyCheckDefinition(
    parse_function=parse_acme_realm,
    detect=DETECT_ACME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9148.3.2.1.2.4.1",
        oids=["2", "3", "5", "7", "11", "30"],
    ),
    service_name="Realm %s",
    discovery_function=inventory_acme_realm,
    check_function=check_acme_realm,
)
