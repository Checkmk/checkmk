#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.gui.time_series import TimeSeries
from cmk.gui.valuespec import Age, Filesize, Float, Integer, Percentage

GraphConsoldiationFunction = Literal["max", "min", "average"]
GraphPresentation = Literal["lines", "stacked", "sum", "average", "min", "max"]
LineType = Literal["line", "area", "stack", "-line", "-area", "-stack"]
Operators = Literal["+", "*", "-", "/", "MAX", "MIN", "AVERAGE", "MERGE"]


@dataclass(frozen=True)
class RRDDataKey:
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: str
    consolidation_func_name: GraphConsoldiationFunction | None
    scale: float


RRDData = Mapping[RRDDataKey, TimeSeries]


class UnitInfo(TypedDict):
    title: str
    symbol: str
    render: Callable[[float], str]
    js_render: str
    id: NotRequired[str]
    stepping: NotRequired[str]
    color: NotRequired[str]
    graph_unit: NotRequired[Callable[[list[float]], tuple[str, list[str]]]]
    description: NotRequired[str]
    valuespec: NotRequired[
        type[Age] | type[Filesize] | type[Float] | type[Integer] | type[Percentage]
    ]
    conversion: NotRequired[Callable[[float], float]]
    perfometer_render: NotRequired[Callable[[float], str]]
    formatter_ident: NotRequired[
        Literal["Decimal", "SI", "IEC", "StandardScientific", "EngineeringScientific", "Time"]
    ]


class ScalarBounds(TypedDict, total=False):
    warn: float
    crit: float
    min: float
    max: float


class TranslatedMetric(TypedDict):
    orig_name: Sequence[str]
    value: float
    scalar: ScalarBounds
    scale: Sequence[float]
    auto_graph: bool
    title: str
    unit: UnitInfo
    color: str
