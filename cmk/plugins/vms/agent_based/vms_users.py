#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<vms_users>>>
# AEP 2 - - 1
# SYSTEM 1
# TCPIP$FTP - - - 1


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except TypeError, ValueError:
        return 0


def discover_vms_users(section: StringTable) -> DiscoveryResult:
    if len(section) > 0:
        yield Service()


def check_vms_users(section: StringTable) -> CheckResult:
    infos = []
    num_sessions = 0
    for line in section:
        # complete missing columns
        padding = [0] * (5 - len(line))
        interactive, _subproc, _batch, _network = list(map(saveint, line[1:])) + padding
        if interactive:
            num_sessions += interactive
            infos.append(f"{line[0]}: {interactive}")

    if num_sessions:
        yield Result(state=State.OK, summary="Interactive users: " + ", ".join(infos))
    else:
        yield Result(state=State.OK, summary="No interactive users")
    yield Metric("sessions", float(num_sessions))


def parse_vms_users(string_table: StringTable) -> StringTable:
    return string_table


agent_section_vms_users = AgentSection(
    name="vms_users",
    parse_function=parse_vms_users,
)

check_plugin_vms_users = CheckPlugin(
    name="vms_users",
    service_name="VMS Users",
    discovery_function=discover_vms_users,
    check_function=check_vms_users,
)
