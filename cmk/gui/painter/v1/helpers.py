#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import NamedTuple, TypeVar

from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.type_defs import Row, Rows
from cmk.gui.view_utils import CellContent, CellSpec

from .painter_lib import PainterConfiguration

T = TypeVar("T")


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


def is_stale(row: Row, *, config: Config) -> bool:
    staleness = row.get("service_staleness", row.get("host_staleness", 0)) or 0
    return staleness >= config.staleness_threshold


def paint_stalified(row: Row, text: CellContent, *, config: Config) -> CellSpec:
    if is_stale(row, config=config):
        return "stale", text
    return "", text


class StrWithStaleness(NamedTuple):
    value: str
    is_stale: bool


def render_str_with_staleness(
    painter_data: StrWithStaleness, painter_configuration: PainterConfiguration, user: LoggedInUser
) -> CellSpec:
    if painter_data.is_stale:
        return "stale", painter_data.value
    return "", painter_data.value


def get_single_str_column(rows: Rows, config: PainterConfiguration) -> Sequence[str]:
    column_name = config.columns[0]
    return [row[column_name] for row in rows]


def get_single_int_column(rows: Rows, config: PainterConfiguration) -> Sequence[int]:
    column_name = config.columns[0]
    return [row[column_name] for row in rows]


def get_single_float_column(rows: Rows, config: PainterConfiguration) -> Sequence[float]:
    column_name = config.columns[0]
    return [row[column_name] for row in rows]
