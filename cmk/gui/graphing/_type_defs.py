#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import assert_never, Literal

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.gui.time_series import TimeSeries

GraphConsolidationFunction = Literal["max", "min", "average"]
GraphPresentation = Literal["lines", "stacked", "sum", "average", "min", "max"]
Operators = Literal["+", "*", "-", "/", "MAX", "MIN", "AVERAGE", "MERGE"]
LineType = Literal["line", "area", "stack", "-line", "-area", "-stack"]


def line_type_mirror(line_type: LineType) -> LineType:
    match line_type:
        case "line":
            return "-line"
        case "-line":
            return "line"
        case "area":
            return "-area"
        case "-area":
            return "area"
        case "stack":
            return "-stack"
        case "-stack":
            return "stack"
        case other:
            assert_never(other)


@dataclass(frozen=True)
class RRDDataKey:
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: str
    consolidation_function: GraphConsolidationFunction | None
    scale: float


RRDData = Mapping[RRDDataKey, TimeSeries]
