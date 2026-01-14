#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Example output from agent:
# Put here the example output from your TCP-Based agent. If the
# check is SNMP-Based, then remove this section


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def discover_tsm_sessions(info):
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
    name="tsm_sessions",
    parse_function=parse_tsm_sessions,
    service_name="tsm_sessions",
    discovery_function=discover_tsm_sessions,
    check_function=check_tsm_sessions,
)
