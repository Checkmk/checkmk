#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"


from cmk.gui.type_defs import Row
from cmk.gui.view_utils import CellContent, CellSpec


def get_perfdata_nth_value(row: Row, n: int, remove_unit: bool = False) -> str:
    perfdata = row.get("service_perf_data")
    if not perfdata:
        return ""
    try:
        parts = perfdata.split()
        if len(parts) <= n:
            return ""  # too few values in perfdata
        _varname, rest = parts[n].split("=")
        number = rest.split(";")[0]
        # Remove unit. Why should we? In case of sorter (numeric)
        if remove_unit:
            while len(number) > 0 and not number[-1].isdigit():
                number = number[:-1]
        return number
    except Exception as e:
        return str(e)


def is_stale(row: Row, staleness_threshold: float) -> bool:
    staleness = row.get("service_staleness", row.get("host_staleness", 0)) or 0
    return staleness >= staleness_threshold


def paint_stalified(row: Row, text: CellContent, staleness_threshold: float) -> CellSpec:
    if is_stale(row, staleness_threshold):
        return "stale", text
    return "", text
