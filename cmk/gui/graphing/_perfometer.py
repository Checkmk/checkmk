#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Any, Literal, NotRequired, TypeAlias, TypedDict

LegacyPerfometer = tuple[str, Any]


class LinearPerfometerSpec(TypedDict):
    type: Literal["linear"]
    segments: Sequence[str]
    total: int | float | str
    condition: NotRequired[str]
    label: NotRequired[tuple[str, str] | None]  # (expression, unit)
    color: NotRequired[str]


class LogarithmicPerfometerSpec(TypedDict):
    type: Literal["logarithmic"]
    metric: str
    half_value: int | float
    exponent: int | float
    unit: NotRequired[str]


class DualPerfometerSpec(TypedDict):
    type: Literal["dual"]
    perfometers: Sequence[LinearPerfometerSpec | LogarithmicPerfometerSpec]


class StackedPerfometerSpec(TypedDict):
    type: Literal["stacked"]
    perfometers: Sequence[LinearPerfometerSpec | LogarithmicPerfometerSpec | DualPerfometerSpec]


PerfometerSpec: TypeAlias = (
    LinearPerfometerSpec | LogarithmicPerfometerSpec | DualPerfometerSpec | StackedPerfometerSpec
)
