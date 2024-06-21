#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.acme import DETECT_ACME


def inventory_acme_agent_sessions(info):
    return [(hostname, None) for hostname, _agent_ty, _state in info]


def check_acme_agent_sessions(item, _no_params, info):
    map_states = {
        "0": (0, "disabled"),
        "1": (2, "out of service"),
        "2": (0, "standby"),
        "3": (0, "in service"),
        "4": (1, "contraints violation"),
        "5": (1, "in service timed out"),
        "6": (1, "oos provisioned response"),
    }
    for hostname, _agent_ty, state in info:
        if item == hostname:
            dev_state, dev_state_readable = map_states[state]
            return dev_state, "Status: %s" % dev_state_readable
    return None


def parse_acme_agent_sessions(string_table: StringTable) -> StringTable:
    return string_table


check_info["acme_agent_sessions"] = LegacyCheckDefinition(
    parse_function=parse_acme_agent_sessions,
    detect=DETECT_ACME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9148.3.2.1.2.2.1",
        oids=["2", "3", "22"],
    ),
    service_name="Agent sessions %s",
    discovery_function=inventory_acme_agent_sessions,
    check_function=check_acme_agent_sessions,
)
