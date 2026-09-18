#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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


def parse_mailman_lists(string_table: StringTable) -> StringTable:
    return string_table


agent_section_mailman_lists = AgentSection(
    name="mailman_lists",
    parse_function=parse_mailman_lists,
)


def discover_mailman_lists(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_mailman_lists(item: str, section: StringTable) -> CheckResult:
    for line in section:
        name, num_members = line[0], saveint(line[1])
        if name == item:
            yield Result(state=State.OK, summary=f"{num_members} members subscribed")
            yield Metric("count", num_members)
            return
    yield Result(state=State.UNKNOWN, summary="List could not be found in agent output")


check_plugin_mailman_lists = CheckPlugin(
    name="mailman_lists",
    service_name="Mailinglist %s",
    discovery_function=discover_mailman_lists,
    check_function=check_mailman_lists,
)
