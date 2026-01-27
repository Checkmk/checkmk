#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="unreachable"

from collections.abc import Callable, Iterable, Mapping
from math import ceil

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckResult
from cmk.agent_based.v2 import get_rate, get_value_store
from cmk.plugins.windows.agent_based.libwmi import (
    get_wmi_time,
    required_tables_missing,
    WMISection,
    WMITable,
)

# This set of functions are used for checks that handle "generic" windows
# performance counters as reported via wmi
# They also work with performance counters reported through other means
# (i.e. pdh) as long as the data transmitted as a csv table.

# Sample data:
# <<<dotnet_clrmemory:sep(44)>>>
# AllocatedBytesPersec,Caption,Description,FinalizationSurvivors,Frequency_Object,...
# 26812621794240,,,32398,0,...
# 2252985000,,,0,0,...

#   .--Parse---------------------------------------------------------------.
#   |                      ____                                            |
#   |                     |  _ \ __ _ _ __ ___  ___                        |
#   |                     | |_) / _` | '__/ __|/ _ \                       |
#   |                     |  __/ (_| | |  \__ \  __/                       |
#   |                     |_|   \__,_|_|  |___/\___|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


# .
#   .--Filters-------------------------------------------------------------.
#   |                     _____ _ _ _                                      |
#   |                    |  ___(_) | |_ ___ _ __ ___                       |
#   |                    | |_  | | | __/ _ \ '__/ __|                      |
#   |                    |  _| | | | ||  __/ |  \__ \                      |
#   |                    |_|   |_|_|\__\___|_|  |___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def wmi_filter_global_only(
    tables: WMISection,
    row: str | int,
) -> bool:
    for table in tables.values():
        try:
            value = table.get(row, "Name")
        except KeyError:
            return False
        if value != "_Global_":
            return False
    return True


# .
#   .--Inventory-----------------------------------------------------------.
#   |            ___                      _                                |
#   |           |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _              |
#   |            | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |             |
#   |            | || | | \ V /  __/ | | | || (_) | |  | |_| |             |
#   |           |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |             |
#   |                                                   |___/              |
#   '----------------------------------------------------------------------'


def inventory_wmi_table_instances(
    tables: WMISection,
    required_tables: Iterable[str] | None = None,
    filt: Callable[[WMISection, str | int], bool] | None = None,
    levels: Mapping[str, object] | None = None,
) -> list[tuple]:
    if required_tables is None:
        required_tables = tables

    if required_tables_missing(tables, required_tables):
        return []

    potential_instances: set = set()
    # inventarize one item per instance that exists in all tables
    for required_table in required_tables:
        table_rows = tables[required_table].row_labels
        if potential_instances:
            potential_instances &= set(table_rows)
        else:
            potential_instances = set(table_rows)

    # don't include the summary line
    potential_instances.discard(None)

    return [(row, levels or {}) for row in potential_instances if filt is None or filt(tables, row)]


def inventory_wmi_table_total(
    tables: WMISection,
    required_tables: Iterable[str] | None = None,
    filt: Callable[[WMISection, None], bool] | None = None,
) -> list[tuple[None, dict]]:
    if required_tables is None:
        required_tables = tables

    if not tables or required_tables_missing(tables, required_tables):
        return []

    if filt is not None and not filt(tables, None):
        return []

    total_present = all(
        None in tables[required_table].row_labels for required_table in required_tables
    )

    if not total_present:
        return []
    return [(None, {})]


# .
#   .--Check---------------------------------------------------------------.
#   |                      ____ _               _                          |
#   |                     / ___| |__   ___  ___| | __                      |
#   |                    | |   | '_ \ / _ \/ __| |/ /                      |
#   |                    | |___| | | |  __/ (__|   <                       |
#   |                     \____|_| |_|\___|\___|_|\_\                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


# to make wato rules simpler, levels are allowed to be passed as tuples if the level
# specifies the upper limit
def get_levels_quadruple(params: tuple | dict[str, tuple] | None) -> tuple | None:
    if params is None:
        return (None, None, None, None)
    if isinstance(params, tuple):
        return (params[0], params[1], None, None)
    upper = params.get("upper") or (None, None)
    lower = params.get("lower") or (None, None)
    return upper + lower


def wmi_yield_raw_persec(
    table: WMITable,
    row: str | int,
    column: str | int,
    infoname: str | None,
    perfvar: str | None,
    levels: tuple | dict[str, tuple] | None = None,
) -> LegacyCheckResult:
    if table is None:
        # This case may be when a check was discovered with a table which subsequently disappeared again.
        # We expect to get `None` in this case.
        return

    if row == "":
        row = 0

    try:
        value = table.get(row, column)
        assert value
    except KeyError:
        return

    value_per_sec = get_rate(
        get_value_store(),
        f"{column}_{table.name}",
        get_wmi_time(table, row),
        int(value),
        raise_overflow=True,
    )

    yield check_levels(
        value_per_sec,
        perfvar,
        get_levels_quadruple(levels),
        infoname=infoname,
    )


def wmi_yield_raw_counter(
    table: WMITable,
    row: str | int,
    column: str | int,
    infoname: str | None,
    perfvar: str | None,
    levels: tuple | dict[str, tuple] | None = None,
    unit: str = "",
) -> LegacyCheckResult:
    if row == "":
        row = 0

    try:
        value = table.get(row, column)
        assert value
    except KeyError:
        return

    yield check_levels(
        int(value),
        perfvar,
        get_levels_quadruple(levels),
        human_readable_func=(lambda x: f"{x} {unit}") if unit else str,
        infoname=infoname,
    )


def wmi_calculate_raw_average(
    table: WMITable,
    row: str | int,
    column: str,
    factor: float,
) -> float:
    if row == "":
        row = 0

    measure = table.get(row, column)
    base = table.get(row, column + "_Base")
    assert measure
    assert base
    base_int = int(base)

    if base_int < 0:
        # this is confusing as hell. why does wmi return this value as a 4 byte signed int
        # when it clearly needs to be unsigned? And how does WMI Explorer know to cast this
        # to unsigned?
        base_int += 1 << 32

    if base_int == 0:
        return 0.0

    return scale_counter(int(measure) * factor, factor, base_int)


def scale_counter(
    measure: float,
    factor: float,
    base: float,
) -> float:
    # This is a total counter which can overflow on long-running systems
    # the following forces the counter into a range of 0.0-1.0, but there is no way to know
    # how often the counter overran, so this may still be wrong
    times = (measure / factor - base) / (1 << 32)
    base += ceil(times) * (1 << 32)
    return measure / base


def wmi_calculate_raw_average_time(
    table: WMITable,
    row: str | int,
    column: str,
) -> float:
    measure = table.get(row, column)
    base = table.get(row, column + "_Base")
    assert measure
    assert base

    sample_time = get_wmi_time(table, row)

    measure_per_sec = get_rate(
        get_value_store(), f"{column}_{table.name}", sample_time, int(measure), raise_overflow=True
    )
    base_per_sec = get_rate(
        get_value_store(),
        f"{column}_{table.name}_Base",
        sample_time,
        int(base),
        raise_overflow=True,
    )

    if base_per_sec == 0:
        return 0
    return measure_per_sec / base_per_sec  # fixed: true-division
