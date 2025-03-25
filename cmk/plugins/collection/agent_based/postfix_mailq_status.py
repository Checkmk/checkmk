#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from enum import Enum

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


class PostfixError(Enum):
    InstanceNotRunning = "PID file exists but instance is not running!"
    PidFileNotReadable = "PID file exists but is not readable"
    SystemNotRunning = "the Postfix mail system is not running"


class PostfixPid(int): ...


def parse_postfix_mailq_status(string_table: StringTable) -> dict[str, PostfixPid | PostfixError]:
    parsed: dict[str, PostfixPid | PostfixError] = {}

    for line in string_table:
        stripped_line = [x.strip() for x in line]
        # In the new agent the main postfix service is now discovered as 'default';
        # in the previous agent version it was simply discovered as 'postfix'.
        # For backward compatibility I therefore convert the queuename
        # from 'postfix' to 'default'.
        queuename = (
            "default"
            if (first_word := stripped_line[0]) in {"default", "postfix"}
            else first_word.split("/")[0]
        )

        status = stripped_line[-1]
        pid = None
        if len(stripped_line) > 2 and stripped_line[-2] == "PID":
            status = stripped_line[-3]
            pid = stripped_line[-1]

        parsed[queuename] = PostfixPid(pid) if pid else PostfixError(status)

    return parsed


agent_section_postfix_mailq_status = AgentSection(
    name="postfix_mailq_status",
    parse_function=parse_postfix_mailq_status,
)


def discovery_postfix_mailq_status(
    section: Mapping[str, PostfixError | PostfixPid],
) -> DiscoveryResult:
    yield from (
        Service(item=queuename)
        for queuename, posfix in section.items()
        if posfix != PostfixError.SystemNotRunning
    )


def check_postfix_mailq_status(
    item: str, section: Mapping[str, PostfixError | PostfixPid]
) -> CheckResult:
    if not (postfix := section.get(item)):
        return

    if isinstance(postfix, PostfixPid):
        yield Result(state=State.OK, summary="Status: the Postfix mail system is running")
        yield Result(state=State.OK, summary=f"PID: {postfix}")
    else:
        yield Result(state=State.CRIT, summary=f"Status: {postfix.value}")


check_plugin_postfix_mailq_status = CheckPlugin(
    name="postfix_mailq_status",
    service_name="Postfix status %s",
    discovery_function=discovery_postfix_mailq_status,
    check_function=check_postfix_mailq_status,
)
