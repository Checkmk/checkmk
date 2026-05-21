#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def _saveint(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_tsm_sessions(string_table: StringTable) -> StringTable:
    return string_table


def discover_tsm_sessions(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_tsm_sessions(section: StringTable) -> CheckResult:
    warn, crit = 300, 600
    state = State.OK
    count = 0
    for entry in section:
        if len(entry) == 4:
            _sid, _client_name, proc_state, wait = entry
        elif len(entry) > 4:
            proc_state, wait = entry[-2:]
        else:
            _sid, proc_state, wait = entry

        if proc_state not in ("RecvW", "MediaW"):
            continue

        wait_seconds = _saveint(wait)
        if wait_seconds >= crit:
            state = State.CRIT
            count += 1
        elif wait_seconds >= warn:
            state = State.worst(state, State.WARN)
            count += 1

    yield Result(
        state=state,
        summary=f"{count} sessions too long in RecvW or MediaW state",
    )


agent_section_tsm_sessions = AgentSection(
    name="tsm_sessions",
    parse_function=parse_tsm_sessions,
)


check_plugin_tsm_sessions = CheckPlugin(
    name="tsm_sessions",
    service_name="tsm_sessions",
    discovery_function=discover_tsm_sessions,
    check_function=check_tsm_sessions,
)
