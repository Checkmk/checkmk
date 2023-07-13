#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

from cmk.base.check_api import (
    get_age_human_readable,
    get_bytes_human_readable,
    LegacyCheckDefinition,
)
from cmk.base.check_legacy_includes.mysql import mysql_parse_per_item
from cmk.base.config import check_info


@mysql_parse_per_item
def parse_mysql_slave(info):
    data: dict[str, int | bool | None] = {}
    for line in info:
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
    state = 0
    perfdata = []
    output = []

    if data["Slave_IO_Running"]:
        output.append("Slave-IO: running")

        if data["Relay_Log_Space"]:
            output.append("Relay Log: %s" % get_bytes_human_readable(data["Relay_Log_Space"]))
            perfdata.append(("relay_log_space", data["Relay_Log_Space"]))

    else:
        output.append("Slave-IO: not running(!!)")
        state = 2

    if data["Slave_SQL_Running"]:
        output.append("Slave-SQL: running")

        # Makes only sense to monitor the age when the SQL slave is running
        if data["Seconds_Behind_Master"] == "NULL":
            output.append("Time behind master: NULL (Lost connection?)(!!)")
            state = 2
        else:
            out = "Time behind Master: %s" % get_age_human_readable(data["Seconds_Behind_Master"])
            warn, crit = params.get("seconds_behind_master", (None, None))
            if crit is not None and data["Seconds_Behind_Master"] > crit:
                state = 2
                out += "(!!)"
            elif warn is not None and data["Seconds_Behind_Master"] > warn:
                state = max(state, 1)
                out += "(!)"
            output.append(out)
            perfdata.append(("sync_latency", data["Seconds_Behind_Master"], warn, crit))
    else:
        output.append("Slave-SQL: not running(!!)")
        state = 2

    yield state, ", ".join(output), perfdata


check_info["mysql_slave"] = LegacyCheckDefinition(
    parse_function=parse_mysql_slave,
    service_name="MySQL DB Slave %s",
    discovery_function=discover_mysql_slave,
    check_function=check_mysql_slave,
    check_ruleset_name="mysql_slave",
)
