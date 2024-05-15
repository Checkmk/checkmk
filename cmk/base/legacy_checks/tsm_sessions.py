#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# Put here the example output from your TCP-Based agent. If the
# check is SNMP-Based, then remove this section


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.config import check_info

from cmk.agent_based.v2 import StringTable


def inventory_tsm_sessions(info):
    yield None, {}


def check_tsm_sessions(item, _no_params, info):
    state = 0
    warn, crit = 300, 600
    count = 0
    for entry in info:
        if len(entry) == 4:
            _sid, _client_name, proc_state, wait = entry
        elif len(entry) > 4:
            proc_state, wait = entry[-2:]
        else:
            _sid, proc_state, wait = entry

        if proc_state in ["RecvW", "MediaW"]:
            wait = saveint(wait)
            if wait >= crit:
                state = 2
                count += 1
            elif wait >= warn:
                state = max(state, 1)
                count += 1
    return state, "%d sessions too long in RecvW or MediaW state" % count


def parse_tsm_sessions(string_table: StringTable) -> StringTable:
    return string_table


check_info["tsm_sessions"] = LegacyCheckDefinition(
    parse_function=parse_tsm_sessions,
    service_name="tsm_sessions",
    discovery_function=inventory_tsm_sessions,
    check_function=check_tsm_sessions,
)
