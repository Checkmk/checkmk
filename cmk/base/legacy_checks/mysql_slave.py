#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

import re
from typing import NamedTuple

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.mysql import mysql_parse_per_item
from cmk.base.config import check_info

from cmk.agent_based.v2 import render, Result, State


class Error(NamedTuple):
    message: str


@mysql_parse_per_item
def parse_mysql_slave(string_table):
    data: dict[str, int | bool | None] = {}
    if len(string_table) == 1:
        line = " ".join(string_table[0])
        if re.match(r"^ERROR [0-9 ()]+ at line \d+:", line):
            return Error(line)

    for line in string_table:
        if not line[0].endswith(":"):
            continue

        key = line[0][:-1]
        val = " ".join(line[1:])

        # Parse some values
        try:
            data[key] = int(val)
        except ValueError:
            data[key] = {"Yes": True, "No": False, "None": None}.get(val, val)

    return data


def discover_mysql_slave(section):
    yield from ((item, {}) for item, data in section.items() if data)


def check_mysql_slave(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    if isinstance(data, Error):
        yield Result(state=State.CRIT, summary=data.message)
        return

    if data["Slave_IO_Running"]:
        yield 0, "Slave-IO: running"

        if rls := data["Relay_Log_Space"]:
            yield check_levels(
                rls, "relay_log_space", None, infoname="Relay log", human_readable_func=render.bytes
            )

    else:
        yield 2, "Slave-IO: not running"

    if not data["Slave_SQL_Running"]:
        yield 2, "Slave-SQL: not running"
        return

    yield 0, "Slave-SQL: running"

    # Makes only sense to monitor the age when the SQL slave is running
    if (sbm := data["Seconds_Behind_Master"]) == "NULL":
        yield 2, "Time behind master: NULL (Lost connection?)"
        return

    yield check_levels(
        sbm,
        "sync_latency",
        params.get("seconds_behind_master"),
        infoname="Time behind master",
        human_readable_func=render.timespan,
    )


check_info["mysql_slave"] = LegacyCheckDefinition(
    parse_function=parse_mysql_slave,
    service_name="MySQL DB Slave %s",
    discovery_function=discover_mysql_slave,
    check_function=check_mysql_slave,
    check_ruleset_name="mysql_slave",
    check_default_parameters={
        "seconds_behind_master": None,
    },
)
