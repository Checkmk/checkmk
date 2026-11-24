#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, kw_only=True)
class Area:
    color: str
    top: Sequence[float | None]


@dataclass(frozen=True, kw_only=True)
class Stack:
    areas: Sequence[Area]


@dataclass(frozen=True, kw_only=True)
class Line:
    color: str
    values: Sequence[float | None]


@dataclass(frozen=True, kw_only=True)
class Region:
    color: str
    lower: Sequence[float | None]
    upper: Sequence[float | None]


@dataclass(frozen=True, kw_only=True)
class Rule:
    color: str
    value: float


@dataclass(frozen=True, kw_only=True)
class AxisLabel:
    position: float
    text: str


@dataclass(frozen=True, kw_only=True)
class VerticalAxis:
    labels: Sequence[AxisLabel] | None


@dataclass(frozen=True, kw_only=True)
class TimeAxis:
    time_zone: str | None


@dataclass(frozen=True, kw_only=True)
class LegendRow:
    color: str
    cells: Sequence[str]


@dataclass(frozen=True, kw_only=True)
class Legend:
    height: float
    header: Sequence[str]
    curves: Sequence[LegendRow]
    rules: Sequence[LegendRow]
    regions: Sequence[LegendRow]


@dataclass(frozen=True, kw_only=True)
class PngDrawing:
    width_inches: float
    height_inches: float
    plot_height: float
    font_size: float
    title: str | None
    caption: str | None
    times: Sequence[int]
    x_range: tuple[int, int]
    y_range: tuple[float, float]
    stacks: Sequence[Stack]
    lines: Sequence[Line]
    regions: Sequence[Region]
    rules: Sequence[Rule]
    vertical_axis: VerticalAxis | None
    time_axis: TimeAxis | None
    legend: Legend | None


@dataclass(frozen=True)
class RenderingFailure:
    message: str

    @classmethod
    def from_exception(cls, exc: Exception) -> Self:
        return cls("".join(traceback.format_exception_only(exc)).strip())
