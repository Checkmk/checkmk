#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import Enum

from cmk.base.plugins.agent_based.agent_based_api.v1 import register
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


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
        queuename = "" if queuename == "postfix" else queuename

        status = stripped_line[-1]
        pid = None
        if len(stripped_line) > 2 and stripped_line[-2] == "PID":
            pid = stripped_line[-1]
            status = stripped_line[-3]

        parsed[queuename] = PostfixPid(pid) if pid else PostfixError(status)

    return parsed


register.agent_section(
    name="postfix_mailq_status",
    parse_function=parse_postfix_mailq_status,
)
