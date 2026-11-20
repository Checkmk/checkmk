#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class AxisLabel:
    position: float
    text: str


@dataclass(frozen=True, kw_only=True)
class VerticalAxis:
    labels: Sequence[AxisLabel] | None


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
