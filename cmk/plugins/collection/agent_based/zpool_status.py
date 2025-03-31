#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any, NamedTuple

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
from cmk.plugins.lib.interfaces import saveint


class ZpoolStatus(NamedTuple):
    message: str = ""
    state_messages: list[str] = []
    error_pools: dict[str, Any] = {}
    warning_pools: dict[str, Any] = {}
    pool_messages: dict[str, Any] = {}


class StateDetails(NamedTuple):
    state: State = State.OK
    message: str = ""


Section = ZpoolStatus

state_mappings = {
    "ONLINE": StateDetails(state=State.OK),
    "DEGRADED": StateDetails(state=State.WARN, message="DEGRADED State"),
    "FAULTED": StateDetails(state=State.CRIT, message="FAULTED State"),
    "UNAVIL": StateDetails(state=State.CRIT, message="UNAVIL State"),
    "REMOVED": StateDetails(state=State.CRIT, message="REMOVED State"),
    "OFFLINE": StateDetails(state=State.OK),
}


def parse_zpool_status(  # pylint: disable=too-many-branches
    string_table: StringTable,
) -> Section | None:
    if not string_table:
        return None

    if " ".join(string_table[0]) == "all pools are healthy":
        return Section(message="All pools are healthy")

    if " ".join(string_table[0]) == "no pools available":
        return Section(message="No pools available")

    start_pool: bool = False
    multiline: bool = False
    last_pool: str = ""
    error_pools: dict[str, Any] = {}
    warning_pools: dict[str, Any] = {}
    pool_messages: dict[str, Any] = {}
    state_messages: list[str] = []

    for line in string_table:
        if line[0] == "pool:":
            last_pool = line[1]
            pool_messages.setdefault(last_pool, [])

        elif line[0] == "state:":
            state_messages.append(line[1])

        elif line[0] in ["status:", "action:"]:
            pool_messages[last_pool].append(" ".join(line[1:]))
            multiline = True

        elif line[0] in ["scrub:", "see:", "scan:", "config:"]:
            multiline = False

        elif line[0] == "NAME":
            multiline = False
            start_pool = True

        elif line[0] == "errors:":
            multiline = False
            start_pool = False
            msg = " ".join(line[1:])
            if msg != "No known data errors":
                pool_messages[last_pool].append(msg)

        elif line[0] in ["spares", "logs", "cache", "special"]:
            start_pool = False
            continue

        elif start_pool is True and not line[0].lower() == "dedup":
            if line[1] != "ONLINE":
                error_pools[line[0]] = tuple(line[1:])
            elif saveint(line[4]) != 0:
                warning_pools[line[0]] = tuple(line[1:])

        elif multiline:
            pool_messages[last_pool].append(" ".join(line))

    return Section(
        state_messages=state_messages,
        error_pools=error_pools,
        warning_pools=warning_pools,
        pool_messages=pool_messages,
    )


def discover_zpool_status(section: Section) -> DiscoveryResult:
    if not section or section.message == "No pools available":
        return
    yield Service()


def check_zpool_status(params: Mapping[str, Any], section: Section) -> CheckResult:
    state: State = State.OK
    messages: list[str] = []

    if section.message == "All pools are healthy":
        state = State.OK
        messages.append(section.message)

    for msg in section.state_messages:
        state_details = state_mappings.get(msg, None)
        if state_details:
            state = state_details.state
            if state_details.message:
                messages.append(state_details.message)
        else:
            state = State.WARN
            messages.append("Unknown State")

    for pool, msg in section.pool_messages.items():
        state = State.WARN
        messages.append("{}: {}".format(pool, " ".join(msg)))

    for pool, msg in section.warning_pools.items():
        state = State.WARN
        messages.append("%s CKSUM: %d" % (pool, saveint(msg[3])))

    for pool, msg in section.error_pools.items():
        state = State.CRIT
        messages.append(f"{pool} state: {msg[0]}")

    if len(messages) == 0:
        messages.append("No critical errors")

    yield Result(state=state, summary=", ".join(messages))


agent_section_zpool_status = AgentSection(
    name="zpool_status",
    parse_function=parse_zpool_status,
)
check_plugin_zpool_status = CheckPlugin(
    name="zpool_status",
    service_name="zpool status",
    discovery_function=discover_zpool_status,
    check_function=check_zpool_status,
    check_ruleset_name="zpool_status",
    check_default_parameters={},
)
