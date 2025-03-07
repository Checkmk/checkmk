#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Annotated, final, Literal

from pydantic import (
    BaseModel,
    computed_field,
    Field,
    field_validator,
    PlainValidator,
    SerializeAsAny,
)

from cmk.ccc.plugin_registry import Registry

from cmk.graphing.v1 import graphs as graphs_api

from ._from_api import RegisteredMetric
from ._graph_render_config import GraphRenderOptions
from ._metric_operation import (
    GraphConsolidationFunction,
    LineType,
    MetricOperation,
    parse_metric_operation,
)
from ._unit import ConvertibleUnitSpecification, NonConvertibleUnitSpecification


class HorizontalRule(BaseModel, frozen=True):
    value: float
    rendered_value: str
    color: str
    title: str


class GraphMetric(BaseModel, frozen=True):
    title: str
    line_type: LineType
    operation: Annotated[SerializeAsAny[MetricOperation], PlainValidator(parse_metric_operation)]
    unit: ConvertibleUnitSpecification
    color: str


class GraphSpecification(BaseModel, ABC, frozen=True):
    @staticmethod
    @abstractmethod
    def graph_type_name() -> str: ...

    @abstractmethod
    def recipes(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    ) -> Sequence[GraphRecipe]: ...

    # mypy does not support other decorators on top of @property:
    # https://github.com/python/mypy/issues/14461
    # https://docs.pydantic.dev/2.0/usage/computed_fields (mypy warning)
    @computed_field  # type: ignore[prop-decorator]
    @property
    @final
    def graph_type(self) -> str:
        return self.graph_type_name()


class GraphSpecificationRegistry(Registry[type[GraphSpecification]]):
    def plugin_name(self, instance: type[GraphSpecification]) -> str:
        return instance.graph_type_name()


graph_specification_registry = GraphSpecificationRegistry()


def parse_raw_graph_specification(raw: object) -> GraphSpecification:
    match raw:
        case GraphSpecification():
            return raw
        case {"graph_type": str(graph_type), **rest}:
            return graph_specification_registry[graph_type].model_validate(rest)
        case dict():
            raise ValueError("Missing 'graph_type' key in graph specification")
    raise TypeError(raw)


class FixedVerticalRange(BaseModel, frozen=True):
    type: Literal["fixed"] = "fixed"
    min: float | None
    max: float | None


class MinimalVerticalRange(BaseModel, frozen=True):
    type: Literal["minimal"] = "minimal"
    min: float | None
    max: float | None


class GraphDataRange(BaseModel, frozen=True):
    time_range: tuple[int, int]
    # Forecast graphs represent step as str (see forecasts.py and fetch_rrd_data)
    # colon separated [step length]:[rrd point count]
    step: int | str
    vertical_range: tuple[float, float] | None = None


class AdditionalGraphHTML(BaseModel, frozen=True):
    title: str
    html: str


class GraphRecipe(BaseModel, frozen=True):
    title: str
    unit_spec: ConvertibleUnitSpecification | NonConvertibleUnitSpecification = Field(
        discriminator="type"
    )
    explicit_vertical_range: FixedVerticalRange | MinimalVerticalRange | None
    horizontal_rules: Sequence[HorizontalRule]
    omit_zero_metrics: bool
    consolidation_function: GraphConsolidationFunction | None
    metrics: Sequence[GraphMetric]
    additional_html: AdditionalGraphHTML | None = None
    render_options: GraphRenderOptions = GraphRenderOptions()
    data_range: GraphDataRange | None = None
    mark_requested_end_time: bool = False
    # https://docs.pydantic.dev/2.4/concepts/serialization/#subclass-instances-for-fields-of-basemodel-dataclasses-typeddict
    # https://docs.pydantic.dev/2.4/concepts/serialization/#serializing-with-duck-typing
    specification: SerializeAsAny[GraphSpecification]

    @field_validator("specification", mode="before")
    def parse_specification(cls, value: Mapping[str, object]) -> GraphSpecification:
        return parse_raw_graph_specification(value)
