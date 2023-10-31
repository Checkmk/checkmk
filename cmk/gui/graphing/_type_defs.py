#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import Any, Literal, NotRequired, TypedDict

GraphConsoldiationFunction = Literal["max", "min", "average"]
GraphPresentation = Literal["lines", "stacked", "sum", "average", "min", "max"]
LineType = Literal["line", "area", "stack", "-line", "-area", "-stack"]
Operators = Literal["+", "*", "-", "/", "MAX", "MIN", "AVERAGE", "MERGE"]


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
    valuespec: NotRequired[Any]  # TODO: better typing
    conversion: NotRequired[Callable[[float], float]]
    perfometer_render: NotRequired[Callable[[float], str]]


class ScalarBounds(TypedDict, total=False):
    warn: float
    crit: float
    min: float
    max: float


class TranslatedMetric(TypedDict):
    orig_name: list[str]
    value: float
    scalar: ScalarBounds
    scale: list[float]
    auto_graph: bool
    title: str
    unit: UnitInfo
    color: str
