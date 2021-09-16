#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from math import ceil
from typing import Callable, Iterable, Optional, Set, Union

from cmk.base.check_api import (
    check_levels,
    get_age_human_readable,
    get_percent_human_readable,
    get_rate,
    MKCounterWrapped,
)
from cmk.base.plugins.agent_based.utils.wmi import get_wmi_time
from cmk.base.plugins.agent_based.utils.wmi import parse_wmi_table as parse_wmi_table_migrated
from cmk.base.plugins.agent_based.utils.wmi import (
    required_tables_missing,
    StringTable,
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


class WMITableLegacy(WMITable):
    """
    Needed since WMITable.get raises IgnoreResultsError
    """

    def get(
        self,
        row: Union[str, int],
        column: Union[str, int],
        silently_skip_timed_out=False,
    ) -> Optional[str]:
        if not silently_skip_timed_out and self.timed_out:
            raise MKCounterWrapped("WMI query timed out")
        return self._get_row_col_value(row, column)


def parse_wmi_table(
    info: StringTable,
    key: str = "Name",
) -> WMISection:
    return parse_wmi_table_migrated(
        info,
        key=key,
        table_type=WMITableLegacy,
    )


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
    row: Union[str, int],
) -> bool:
    for table in tables.values():
        try:
            value = table.get(row, "Name", silently_skip_timed_out=True)
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
    required_tables: Optional[Iterable[str]] = None,
    filt: Optional[Callable[[WMISection, Union[str, int]], bool]] = None,
    levels=None,
):
    if required_tables is None:
        required_tables = tables

    if required_tables_missing(tables, required_tables):
        return []

    potential_instances: Set = set()
    # inventarize one item per instance that exists in all tables
    for required_table in required_tables:
        table_rows = tables[required_table].row_labels
        if potential_instances:
            potential_instances &= set(table_rows)
        else:
            potential_instances = set(table_rows)

    # don't include the summary line
    potential_instances.discard(None)

    return [(row, levels) for row in potential_instances if filt is None or filt(tables, row)]


def inventory_wmi_table_total(
    tables: WMISection,
    required_tables: Optional[Iterable[str]] = None,
    filt: Optional[Callable[[WMISection, None], bool]] = None,
    levels=None,
):
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
    return [(None, levels)]


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
def get_levels_quadruple(params):
    if params is None:
        return (None, None, None, None)
    if isinstance(params, tuple):
        return (params[0], params[1], None, None)
    upper = params.get("upper") or (None, None)
    lower = params.get("lower") or (None, None)
    return upper + lower


def wmi_yield_raw_persec(
    table: WMITable,
    row: Union[str, int],
    column: Union[str, int],
    infoname: Optional[str],
    perfvar: Optional[str],
    levels=None,
):
    if table is None:
        # This case may be when a check was discovered with a table which subsequently
        # disappeared again. We expect to get None in this case and return some "nothing happened"
        return 0, "", []

    if row == "":
        row = 0

    try:
        value = table.get(row, column)
        assert value
    except KeyError:
        return 3, "Item not present anymore", []

    value_per_sec = get_rate("%s_%s" % (column, table.name), get_wmi_time(table, row), int(value))

    return check_levels(
        value_per_sec,
        perfvar,
        get_levels_quadruple(levels),
        infoname=infoname,
    )


def wmi_yield_raw_counter(
    table: WMITable,
    row: Union[str, int],
    column: Union[str, int],
    infoname: Optional[str],
    perfvar: Optional[str],
    levels=None,
    unit: str = "",
):
    if row == "":
        row = 0

    try:
        value = table.get(row, column)
        assert value
    except KeyError:
        return 3, "counter %r not present anymore" % ((row, column),), []

    return check_levels(
        int(value),
        perfvar,
        get_levels_quadruple(levels),
        infoname=infoname,
        unit=unit,
        human_readable_func=str,
    )


def wmi_calculate_raw_average(
    table: WMITable,
    row: Union[str, int],
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
    row: Union[str, int],
    column: str,
) -> float:
    measure = table.get(row, column)
    base = table.get(row, column + "_Base")
    assert measure
    assert base

    sample_time = get_wmi_time(table, row)

    measure_per_sec = get_rate("%s_%s" % (column, table.name), sample_time, int(measure))
    base_per_sec = get_rate("%s_%s_Base" % (column, table.name), sample_time, int(base))

    if base_per_sec == 0:
        return 0
    return measure_per_sec / base_per_sec  # fixed: true-division


def wmi_yield_raw_average(
    table: WMITable,
    row: Union[str, int],
    column: str,
    infoname: Optional[str],
    perfvar: Optional[str],
    levels=None,
    perfscale: float = 1.0,
):
    try:
        average = wmi_calculate_raw_average(table, row, column, 1) * perfscale
    except KeyError:
        return 3, "item not present anymore", []

    return check_levels(
        average,
        perfvar,
        get_levels_quadruple(levels),
        infoname=infoname,
        human_readable_func=get_age_human_readable,
    )


def wmi_yield_raw_average_timer(
    table: WMITable,
    row: Union[str, int],
    column: str,
    infoname: Optional[str],
    perfvar: Optional[str],
    levels=None,
):
    assert table.frequency
    try:
        average = (
            wmi_calculate_raw_average_time(
                table,
                row,
                column,
            )
            / table.frequency
        )  # fixed: true-division
    except KeyError:
        return 3, "item not present anymore", []

    return check_levels(
        average,
        perfvar,
        get_levels_quadruple(levels),
        infoname=infoname,
    )


def wmi_yield_raw_fraction(
    table: WMITable,
    row: Union[str, int],
    column: str,
    infoname: Optional[str],
    perfvar: Optional[str],
    levels=None,
):
    try:
        average = wmi_calculate_raw_average(table, row, column, 100)
    except KeyError:
        return 3, "item not present anymore", []

    return check_levels(
        average,
        perfvar,
        get_levels_quadruple(levels),
        infoname=infoname,
        human_readable_func=get_percent_human_readable,
        boundaries=(0, 100),
    )


# .
