#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import time
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    render,
    Result,
    Service,
    State,
    StringTable,
)

# <<<mssql_backup>>>
# MSSQL_SQLEXPRESS1 test123 1331207325

# <<<mssql_backup>>>
# MSSQL_SQL0x2 master 2016-07-08 20:20:27
# MSSQL_SQL0x2 model 2016-07-08 20:20:28
# MSSQL_SQL0x2 model 2016-07-12 09:09:42
# MSSQL_SQL0x2 model 2016-07-11 20:20:07
# MSSQL_SQL0x2 msdb 2016-07-08 20:20:43
# MSSQL_SQL0x2 msdb 2016-07-11 20:20:07

# <<<mssql_backup>>>
# MSSQL_SQL0x3 master 2016-07-08 20:20:27 D
# MSSQL_SQL0x3 model 2016-07-08 20:20:28 D
# MSSQL_SQL0x3 model 2016-07-12 09:09:42 L
# MSSQL_SQL0x3 model 2016-07-11 20:20:07 I
# MSSQL_SQL0x3 msdb 2016-07-08 20:20:43 D
# MSSQL_SQL0x3 msdb 2016-07-11 20:20:07 I

# <<<mssql_backup:sep(124)>>>
# MSSQL_SQL0x4|master|2016-07-08 20:20:27|D
# MSSQL_SQL0x4|model|2016-07-08 20:20:28|D
# MSSQL_SQL0x4|model|2016-07-12 09:09:42|L
# MSSQL_SQL0x4|model|2016-07-11 20:20:07|I
# MSSQL_SQL0x4|msdb|2016-07-08 20:20:43|D
# MSSQL_SQL0x4|msdb|2016-07-11 20:20:07|I

# <<<mssql_backup:sep(124)>>>
# MSSQL_SQL0x4|master|2016-07-08 20:20:27+00:00|D
# ...


class Backup(NamedTuple):
    timestamp: float | None
    type: str | None
    state: str


Section = Mapping[str, Sequence[Backup]]


_MAP_BACKUP_TYPES = {
    "D": "database",
    "I": "database diff",
    "L": "log",
    "F": "file or filegroup",
    "G": "file diff",
    "P": "partial",
    "Q": "partial diff",
    "-": "unspecific",
}


def _parse_date_and_time(b_date: str, b_time: str | None) -> float | None:
    try:
        if b_time is None:
            return int(b_date)

        tz = None
        if "+" in b_time:
            b_time, tz = b_time.split("+")

        result = datetime.datetime.strptime(f"{b_date} {b_time}", "%Y-%m-%d %H:%M:%S")

        if tz == "00:00":  # only +00:00 is currently supported
            result = result.replace(tzinfo=datetime.UTC)

        return result.timestamp()
    except ValueError:
        return None


def _get_word(line: Sequence[str], idx: int) -> str | None:
    try:
        return line[idx]
    except IndexError:
        return None


def parse_mssql_backup(string_table: StringTable) -> Section:
    parsed: dict[str, list[Backup]] = {}

    line: Sequence[str | None]
    for line in string_table:
        if len(line) <= 2:
            continue
        # handle one special case where spaces are in date/time:
        if len(line) == 4 and " " in line[2]:
            line = line[:2] + line[2].split(" ") + line[3:]

        inst, tablespace, b_date = line[:3]
        # (fill up with Nones)
        b_time, b_type, b_state = (_get_word(line, i) for i in (3, 4, 5))

        timestamp = _parse_date_and_time(b_date, b_time)

        item = f"{inst} {tablespace}"
        backup = Backup(timestamp, _MAP_BACKUP_TYPES.get(b_type) if b_type else None, b_state or "")
        parsed.setdefault(item, []).append(backup)

    return parsed


agent_section_mssql_backup = AgentSection(
    name="mssql_backup",
    parse_function=parse_mssql_backup,
)


def discover_mssql_backup(params: Mapping[str, Any], section: Section) -> DiscoveryResult:
    if params["mode"] != "summary":
        return
    for db_name in section:
        yield Service(item=db_name)


def check_mssql_backup(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    data = section.get(item)
    if data is None:
        # Assume general connection problem to the database, which is reported
        # by the "X Instance" service and skip this check.
        raise IgnoreResultsError("Failed to connect to database")

    for backup in data:
        if backup.state == "no backup found":
            yield Result(state=State(params.get("not_found", 1)), summary="No backup found")
            continue
        if backup.state.startswith("ERROR: "):
            yield Result(state=State.CRIT, summary=backup.state[7:])
            continue
        if backup.type is None:
            backup_type_var = "database"
            perfkey = "seconds"
            backup_type_info = "[database]"
        else:
            backup_type_var = backup.type.strip().replace(" ", "_")
            perfkey = "backup_age_%s" % backup_type_var
            backup_type_info = "[%s]" % backup.type
        yield Result(
            state=State.OK,
            summary=f"{backup_type_info} Last backup: {render.datetime(backup.timestamp)}",
        )
        if backup.timestamp is None:
            return
        if (age := time.time() - backup.timestamp) < 0:
            yield Result(
                state=State.WARN,
                summary="Cannot reasonably calculate time since last backup (hosts time is running ahead), "
                f"Time since last backup: -{render.timespan(abs(age))}",
            )
            return
        yield from check_levels(
            age,
            metric_name=perfkey,
            levels_upper=params.get(backup_type_var),
            render_func=render.timespan,
            label="Time since last backup",
        )


check_plugin_mssql_backup = CheckPlugin(
    name="mssql_backup",
    service_name="MSSQL %s Backup",
    discovery_function=discover_mssql_backup,
    discovery_ruleset_name="discovery_mssql_backup",
    discovery_default_parameters={"mode": "summary"},
    check_function=check_mssql_backup,
    check_ruleset_name="mssql_backup",
    check_default_parameters={
        "database": ("no_levels", None),
        "database_diff": ("no_levels", None),
        "log": ("no_levels", None),
        "file_or_filegroup": ("no_levels", None),
        "file_diff": ("no_levels", None),
        "partial": ("no_levels", None),
        "partial_diff": ("no_levels", None),
        "unspecific": ("no_levels", None),
    },
)


# .
#   .--single--------------------------------------------------------------.
#   |                          _             _                             |
#   |                      ___(_)_ __   __ _| | ___                        |
#   |                     / __| | '_ \ / _` | |/ _ \                       |
#   |                     \__ \ | | | | (_| | |  __/                       |
#   |                     |___/_|_| |_|\__, |_|\___|                       |
#   |                                  |___/                               |
#   '----------------------------------------------------------------------'


def _mssql_backup_per_type_item(db_name: str, backup: Backup) -> str:
    if backup.type is None:
        return "%s UNKNOWN" % db_name
    return f"{db_name} {backup.type.title()}"


def discover_mssql_backup_per_type(params: Mapping[str, Any], section: Section) -> DiscoveryResult:
    if params["mode"] != "per_type":
        return
    for db_name, attrs in section.items():
        for backup in attrs:
            yield Service(item=_mssql_backup_per_type_item(db_name, backup))


def check_mssql_backup_per_type(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    for db_name, attrs in section.items():
        for backup in attrs:
            if item == _mssql_backup_per_type_item(db_name, backup):
                yield Result(
                    state=State.OK,
                    summary=f"Last backup: {render.datetime(backup.timestamp)}",
                )
                if backup.timestamp is None:
                    return
                if (age := time.time() - backup.timestamp) < 0:
                    yield Result(
                        state=State.WARN,
                        summary="Cannot reasonably calculate time since last backup (hosts time is running ahead), "
                        f"Time since last backup: -{render.timespan(abs(age))}",
                    )
                    return
                yield from check_levels(
                    age,
                    metric_name="backup_age",
                    levels_upper=params.get("levels"),
                    render_func=render.timespan,
                    label="Time since last backup",
                )
                return
    # Assume general connection problem to the database, which is reported
    # by the "X Instance" service and skip this check.
    raise IgnoreResultsError("Failed to connect to database")


check_plugin_mssql_backup_per_type = CheckPlugin(
    name="mssql_backup_per_type",
    service_name="MSSQL %s Backup",
    sections=["mssql_backup"],
    discovery_function=discover_mssql_backup_per_type,
    discovery_ruleset_name="discovery_mssql_backup",
    discovery_default_parameters={"mode": "summary"},
    check_function=check_mssql_backup_per_type,
    check_ruleset_name="mssql_backup_per_type",
    check_default_parameters={},
)
