#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal, override

from ._graph_metric_expressions import GraphConsolidationFunction
from ._graph_specification import (
    GraphMetric,
    GraphSpecification,
    HorizontalRule,
)
from ._unit import ConvertibleUnitSpecification


class ExplicitGraphSpecification(GraphSpecification, frozen=True):
    title: str
    unit: ConvertibleUnitSpecification
    consolidation_function: GraphConsolidationFunction | None
    explicit_vertical_range: tuple[float, float] | None
    omit_zero_metrics: bool
    horizontal_rules: Sequence[HorizontalRule]
    metrics: Sequence[GraphMetric]
    mark_requested_end_time: bool = False

    @staticmethod
    @override
    def graph_type_name() -> Literal["explicit"]:
        return "explicit"
