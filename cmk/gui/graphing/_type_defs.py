#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, TypedDict

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.gui.time_series import TimeSeries

from ._unit_info import UnitInfo

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


class ScalarBounds(TypedDict, total=False):
    warn: float
    crit: float
    min: float
    max: float


@dataclass(frozen=True)
class TranslatedMetric:
    orig_name: Sequence[str]
    value: float
    scalar: ScalarBounds
    scale: Sequence[float]
    auto_graph: bool
    title: str
    unit_info: UnitInfo
    color: str
