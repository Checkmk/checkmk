#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Final, Literal

from ._graph_specification import (
    ExplicitGraphSpecification,
    GraphMetric,
    GraphRecipe,
    GraphRecipeNew,
    GraphSpecificationNew,
    HorizontalRule,
)
from ._type_defs import GraphConsoldiationFunction


class ExplicitGraphRecipeBuilder:
    def __init__(self) -> None:
        self.graph_type: Final = "explicit"

    def __call__(self, spec: ExplicitGraphSpecification) -> list[GraphRecipe]:
        return [
            GraphRecipe(
                title=spec.title,
                unit=spec.unit,
                consolidation_function=spec.consolidation_function,
                explicit_vertical_range=spec.explicit_vertical_range,
                omit_zero_metrics=spec.omit_zero_metrics,
                horizontal_rules=spec.horizontal_rules,
                metrics=spec.metrics,
                specification=spec,
                mark_requested_end_time=spec.mark_requested_end_time,
            )
        ]


class ExplicitGraphSpecificationNew(GraphSpecificationNew, frozen=True):
    graph_type: Literal["explicit"] = "explicit"
    title: str
    unit: str
    consolidation_function: GraphConsoldiationFunction | None
    explicit_vertical_range: tuple[float | None, float | None]
    omit_zero_metrics: bool
    horizontal_rules: Sequence[HorizontalRule]
    metrics: Sequence[GraphMetric]
    mark_requested_end_time: bool = False

    @staticmethod
    def name() -> str:
        return "explicit_graph_specification"

    def recipes(self) -> list[GraphRecipeNew]:
        return [
            GraphRecipeNew(
                title=self.title,
                unit=self.unit,
                consolidation_function=self.consolidation_function,
                explicit_vertical_range=self.explicit_vertical_range,
                omit_zero_metrics=self.omit_zero_metrics,
                horizontal_rules=self.horizontal_rules,
                metrics=self.metrics,
                specification=self,
                mark_requested_end_time=self.mark_requested_end_time,
            )
        ]
