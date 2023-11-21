#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from enum import Enum

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)


class PostfixError(Enum):
    InstanceNotRunning = "PID file exists but instance is not running!"
    PidFileNotReadable = "PID file exists but is not readable"
    SystemNotRunning = "the Postfix mail system is not running"


class PostfixPid(int):
    ...


def parse_postfix_mailq_status(string_table: StringTable) -> dict[str, PostfixPid | PostfixError]:
    parsed: dict[str, PostfixPid | PostfixError] = {}

    for line in string_table:
        stripped_line = [x.strip() for x in line]
        queuename = stripped_line[0].split("/")[0]

        status = stripped_line[-1]
        pid = None
        if len(stripped_line) > 2 and stripped_line[-2] == "PID":
            status = stripped_line[-3]
            pid = stripped_line[-1]

        parsed[queuename] = PostfixPid(pid) if pid else PostfixError(status)

    return parsed


register.agent_section(
    name="postfix_mailq_status",
    parse_function=parse_postfix_mailq_status,
)


def discovery_postfix_mailq_status(
    section: Mapping[str, PostfixError | PostfixPid]
) -> DiscoveryResult:
    yield from (Service(item=queuename) for queuename in section)


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


register.check_plugin(
    name="postfix_mailq_status",
    service_name="Postfix status %s",
    discovery_function=discovery_postfix_mailq_status,
    check_function=check_postfix_mailq_status,
)
