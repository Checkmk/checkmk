#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

from ._from_api import RegisteredMetric
from ._graph_specification import (
    FixedVerticalRange,
    GraphMetric,
    GraphRecipe,
    GraphSpecification,
    HorizontalRule,
)
from ._metric_operation import GraphConsolidationFunction
from ._unit import ConvertibleUnitSpecification


class ExplicitGraphSpecification(GraphSpecification, frozen=True):
    title: str
    unit: ConvertibleUnitSpecification
    consolidation_function: GraphConsolidationFunction | None
    explicit_vertical_range: tuple[float | None, float | None]
    omit_zero_metrics: bool
    horizontal_rules: Sequence[HorizontalRule]
    metrics: Sequence[GraphMetric]
    mark_requested_end_time: bool = False

    @staticmethod
    def graph_type_name() -> Literal["explicit"]:
        return "explicit"

    def recipes(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
    ) -> list[GraphRecipe]:
        return [
            GraphRecipe(
                title=self.title,
                unit_spec=self.unit,
                consolidation_function=self.consolidation_function,
                explicit_vertical_range=FixedVerticalRange(
                    min=self.explicit_vertical_range[0],
                    max=self.explicit_vertical_range[1],
                ),
                omit_zero_metrics=self.omit_zero_metrics,
                horizontal_rules=self.horizontal_rules,
                metrics=self.metrics,
                specification=self,
                mark_requested_end_time=self.mark_requested_end_time,
            )
        ]
