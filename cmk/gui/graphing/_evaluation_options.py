#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.graphing_engine import ConsolidationFunction, TimeRange


@dataclass(frozen=True, kw_only=True)
class EvaluationOptions:
    time_range: TimeRange
    consolidation_function: ConsolidationFunction
    destination: str | None
    combination_mode: str | None = None
    include_edge_neighbours: bool = False
