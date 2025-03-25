#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
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

# <<<mssql_tablespaces>>>
# MSSQL_SQLEXPRESS master 5.25 MB 1.59 MB 2464 KB 1096 KB 1024 KB 344 KB
# MSSQL_SQLEXPRESS model 3.00 MB 1.13 MB 1152 KB 472 KB 632 KB 48 KB
# MSSQL_SQLEXPRESS msdb 18.13 MB 4.05 MB 10960 KB 8336 KB 2080 KB 544 KB
# MSSQL_SQLEXPRESS tempdb 2.75 MB 1.08 MB 1200 KB 480 KB 672 KB 48 KB
# MSSQL_SQLEXPRESS test123 4.00 MB 1.78 MB 1248 KB 528 KB 648 KB 72 KB
#  0: process instance
#  1: tablespace name
#  2: db size (Size of the current database in megabytes.
#     database_size includes both data and log files.)
#  3: uom
#  4: unallocated space (Space in the database that has not been reserved for database objects.)
#  5: uom
#  6: reserved space (Total amount of space allocated by objects in the database.)
#  7: uom
#  8: Total amount of space used by data.
#  9: uom
# 10: Total amount of space used by indexes.
# 11: uom
# 12: Total amount of space reserved for objects in the database, but not yet used.
# 13: uom


@dataclass(frozen=True)
class MSSQLTableSpace:
    size: float | None
    unallocated: float | None
    reserved: float | None
    data: float | None
    indexes: float | None
    unused: float | None
    error: str | None


SectionTableSpaces = Mapping[str, MSSQLTableSpace]

LevelsType = tuple[float | int, float | int]


def parse(string_table: StringTable) -> SectionTableSpaces:
    def to_bytes(value, uom):
        exponent = {"KB": 1, "MB": 2, "GB": 3, "TB": 4}.get(uom, 0)
        try:
            return float(value) * (1024**exponent)
        except ValueError:
            return None

    section = {}
    for line in string_table:
        if len(line) < 14:
            continue

        pairs = list(zip(line[:14:2], line[1:14:2]))
        values = (to_bytes(*p) for p in pairs[1:])

        keys = ("size", "unallocated", "reserved", "data", "indexes", "unused")
        data = dict(zip(keys, values))

        data["error"] = (
            " ".join(line[15:]) if len(line) > 14 and line[14].startswith("ERROR:") else None
        )

        item = f"{line[0]} {line[1]}"
        section[item] = MSSQLTableSpace(**data)
    return section


def discover(section: SectionTableSpaces) -> DiscoveryResult:
    for item, tablespace in section.items():
        if not tablespace.error:
            yield Service(item=item)


agent_section_mssql_tablespaces = AgentSection(name="mssql_tablespaces", parse_function=parse)


def _levels_are_in_percentage(levels: LevelsType | None) -> bool:
    # Oldschool type dispatch :-(
    return levels is not None and isinstance(levels[1], float)


def check(item: str, params: Mapping[str, Any], section: SectionTableSpaces) -> CheckResult:
    tablespace = section.get(item)
    if tablespace is None:
        # Assume general connection problem to the database, which is reported
        # by the "X Instance" service and skip this check.
        raise IgnoreResultsError("Tablespace not found")

    size = tablespace.size
    if tablespace.error:
        yield Result(state=State.CRIT, summary=tablespace.error)

    if size is not None:
        yield from check_levels_v1(
            value=size,
            metric_name="size",
            levels_upper=params.get("size"),
            render_func=render.bytes,
            label="Size",
        )

    for metric_name, value_bytes, label, levels_lower, levels_upper in [
        (
            "unallocated",
            tablespace.unallocated,
            "Unallocated space",
            params.get("unallocated"),
            None,
        ),
        ("reserved", tablespace.reserved, "Reserved space", None, params.get("reserved")),
        ("data", tablespace.data, "Data", None, params.get("data")),
        ("indexes", tablespace.indexes, "Indexes", None, params.get("indexes")),
        ("unused", tablespace.unused, "Unused", None, params.get("unused")),
    ]:
        if value_bytes is None:
            continue

        levels_are_perc = _levels_are_in_percentage(levels_upper or levels_lower)

        yield from check_levels_v1(
            value=value_bytes,
            metric_name=metric_name,
            levels_upper=None if levels_are_perc else levels_upper,
            levels_lower=None if levels_are_perc else levels_lower,
            render_func=render.bytes,
            label=label,
        )
        if size is not None and size != 0:
            yield from check_levels_v1(
                value=100.0 * value_bytes / size,
                levels_upper=levels_upper if levels_are_perc else None,
                levels_lower=levels_lower if levels_are_perc else None,
                render_func=render.percent,
            )


check_plugin_mssql_tablespaces = CheckPlugin(
    name="mssql_tablespaces",
    service_name="MSSQL %s Sizes",
    discovery_function=discover,
    check_function=check,
    check_default_parameters={},
    check_ruleset_name="mssql_tablespaces",
)
