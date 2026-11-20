#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from zoneinfo import ZoneInfo

from cmk.graphing_engine import EvaluatedGraph, EvaluatedVerticalRange, NonConvertibleUnit, Unit


@dataclass(frozen=True, kw_only=True)
class PngOptions:
    size: tuple[float, float]
    font_size: float
    show_title: bool
    show_legend: bool
    show_vertical_axis: bool
    show_time_axis: bool
    show_graph_time: bool


@dataclass(frozen=True, kw_only=True)
class PngTexts:
    minimum: str
    maximum: str
    average: str
    last: str
    date_format: str
    caption: str


@dataclass(frozen=True, kw_only=True)
class PngGraph:
    graph: EvaluatedGraph
    options: PngOptions
    y_axis_unit: Unit | NonConvertibleUnit | None
    requested_vertical_range: EvaluatedVerticalRange | None
    # None: the site's local zone. An export passes the browser's zone, so that its time
    # axis matches the one of the Vue graph.
    time_zone: ZoneInfo | None
    # The graph is fetched with the samples just beyond the range it shows, as the Vue graph
    # is, so that the curves are drawn in from them up to the axes.
    visible_time_range: tuple[int, int]
