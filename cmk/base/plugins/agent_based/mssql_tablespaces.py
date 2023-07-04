#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Tuple, Union

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    IgnoreResultsError,
    Metric,
    register,
    render,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
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
    size: Optional[float]
    unallocated: Optional[float]
    reserved: Optional[float]
    data: Optional[float]
    indexes: Optional[float]
    unused: Optional[float]
    error: Optional[str]


SectionTableSpaces = Mapping[str, MSSQLTableSpace]

LevelsType = Tuple[Union[float, int], Union[float, int]]


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

        data["error"] = (" ".join(line[15:])
                         if len(line) > 14 and line[14].startswith("ERROR:") else None)

        item = f"{line[0]} {line[1]}"
        section[item] = MSSQLTableSpace(**data)
    return section


def discover(section: SectionTableSpaces) -> DiscoveryResult:
    for item, tablespace in section.items():
        if not tablespace.error:
            yield Service(item=item)


register.agent_section(name="mssql_tablespaces", parse_function=parse)


def _get_check_value(levels: LevelsType, value_bytes: float,
                     value_perc: Optional[float]) -> Tuple[float, Callable[[float], str]]:
    if isinstance(levels[1], float) and value_perc is not None:
        return value_perc, render.percent
    return value_bytes, render.bytes


def _check_levels_space_upper(
    value_bytes: float,
    value_perc: Optional[float],
    metric_name: str,
    levels: LevelsType,
    infotext: str,
) -> CheckResult:
    value, render_func = _get_check_value(levels, value_bytes, value_perc)

    warn, crit = levels
    state = State.OK
    if value >= crit:
        state = State.CRIT
    elif value >= warn:
        state = State.WARN
    if state:
        infotext = f"{infotext} (warn/crit at {render_func(warn)}/{render_func(crit)})"

    yield Result(state=state, summary=infotext)
    yield Metric(name=metric_name, value=value_bytes)


def _check_levels_space_lower(
    value_bytes: float,
    value_perc: Optional[float],
    metric_name: str,
    levels: LevelsType,
    infotext: str,
) -> CheckResult:
    value, render_func = _get_check_value(levels, value_bytes, value_perc)

    warn, crit = levels
    state = State.OK
    if value <= crit:
        state = State.CRIT
    elif value <= warn:
        state = State.WARN
    if state:
        infotext = f"{infotext} (warn/crit below {render_func(warn)}/{render_func(crit)})"

    yield Result(state=state, summary=infotext)
    yield Metric(name=metric_name, value=value_bytes)


def cluster_check(item: str, params: Mapping[str, Any],
                  section: Mapping[str, Optional[SectionTableSpaces]]) -> CheckResult:

    cluster_section = {
        section_item: section_data for node_section in reversed(list(section.values()))
        if node_section is not None for section_item, section_data in node_section.items()
    }

    yield from check(item, params, cluster_section)


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
        levels = params.get("size", (None, None))
        yield from check_levels(
            value=size,
            metric_name="size",
            levels_upper=levels,
            render_func=render.bytes,
            label="Size",
        )

    for metric_name, value_bytes, label, check_levels_space in [
        ("unallocated", tablespace.unallocated, "Unallocated space", _check_levels_space_lower),
        ("reserved", tablespace.reserved, "Reserved space", _check_levels_space_upper),
        ("data", tablespace.data, "Data", _check_levels_space_upper),
        ("indexes", tablespace.indexes, "Indexes", _check_levels_space_upper),
        ("unused", tablespace.unused, "Unused", _check_levels_space_upper),
    ]:
        if value_bytes is None:
            continue

        if size is None or size == 0:
            value_perc = None
            infotext = f"{label}: {render.bytes(value_bytes)}"
        else:
            value_perc = 100.0 * value_bytes / size
            infotext = f"{label}: {render.bytes(value_bytes)}, {render.percent(value_perc)}"

        if (levels := params.get(metric_name)) is None:
            yield Result(state=State.OK, summary=infotext)
            yield Metric(name=metric_name, value=value_bytes)
            continue

        yield from check_levels_space(value_bytes, value_perc, metric_name, levels, infotext)


register.check_plugin(
    name="mssql_tablespaces",
    service_name="MSSQL %s Sizes",
    discovery_function=discover,
    check_function=check,
    cluster_check_function=cluster_check,
    check_default_parameters={},
    check_ruleset_name="mssql_tablespaces",
)
