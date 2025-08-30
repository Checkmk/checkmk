#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, TypedDict

from annotated_types import Ge

from cmk.gui.dashboard.type_defs import ResponsiveGridBreakpoint


class _BreakpointConfig(TypedDict):
    min_width: Annotated[int, Ge(0)]
    columns: Annotated[int, Ge(1)]


RESPONSIVE_GRID_BREAKPOINTS: dict[ResponsiveGridBreakpoint, _BreakpointConfig] = {
    "XS": {"min_width": 280, "columns": 4},
    "S": {"min_width": 535, "columns": 8},
    "M": {"min_width": 705, "columns": 12},
    "L": {"min_width": 961, "columns": 12},
    "XL": {"min_width": 1217, "columns": 24},
}
