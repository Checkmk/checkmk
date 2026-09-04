#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Annotated, final, override

from pydantic import (
    BaseModel,
    computed_field,
    PlainValidator,
    SerializeAsAny,
)

from cmk.ccc.plugin_registry import Registry
from cmk.gui.type_defs import SizeMM
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.temperate_unit import TemperatureUnit

from ._from_api import GraphFromAPI, RegisteredMetric
from ._graph_metric_expressions import (
    GraphMetricExpression,
    line_type_mirror,
    LineType,
    parse_graph_metric_expression,
)
from ._metric_backend_registry import FetchTimeSeriesProtocol
from ._unit import ConvertibleUnitSpecification


@dataclass(frozen=True)
class GraphEnvironment:
    """Bundles the server-side environment passed unchanged through every rendering path."""

    registered_metrics: Mapping[str, RegisteredMetric]
    registered_graphs: Mapping[str, GraphFromAPI]
    user_permissions: UserPermissions
    temperature_unit: TemperatureUnit
    backend_time_series_fetcher: FetchTimeSeriesProtocol | None
    debug: bool = False


class HorizontalRule(BaseModel, frozen=True):
    value: float
    rendered_value: str
    color: str
    title: str


class GraphMetric(BaseModel, frozen=True):
    title: str
    line_type: LineType
    operation: Annotated[
        SerializeAsAny[GraphMetricExpression], PlainValidator(parse_graph_metric_expression)
    ]
    unit: ConvertibleUnitSpecification
    color: str

    def mirror(self) -> GraphMetric:
        return GraphMetric(
            title=self.title,
            line_type=line_type_mirror(self.line_type),
            operation=self.operation,
            unit=self.unit,
            color=self.color,
        )


class GraphSpecification(BaseModel, ABC, frozen=True):
    id: str | None = None

    @staticmethod
    @abstractmethod
    def graph_type_name() -> str: ...

    # mypy does not support other decorators on top of @property:
    # https://github.com/python/mypy/issues/14461
    # https://docs.pydantic.dev/2.0/usage/computed_fields (mypy warning)
    @computed_field  # type: ignore[prop-decorator]
    @property
    @final
    def graph_type(self) -> str:
        return self.graph_type_name()

    @classmethod
    def add_visual_type(cls) -> str | None:
        return None


class GraphSpecificationRegistry(Registry[type[GraphSpecification]]):
    @override
    def plugin_name(self, instance: type[GraphSpecification]) -> str:
        return instance.graph_type_name()


graph_specification_registry = GraphSpecificationRegistry()


def parse_graph_specification(graph_specification: object) -> GraphSpecification:
    match graph_specification:  # type: ignore[exhaustive-match]
        case GraphSpecification():
            return graph_specification
        case {"graph_type": str(graph_type), **rest}:
            return graph_specification_registry[graph_type].model_validate(rest)
        case dict():
            raise ValueError("Missing 'graph_type' key in graph specification")
    raise TypeError(graph_specification)


class GraphRanges(BaseModel, frozen=True):
    time_range: tuple[int, int]
    step: int
    vertical_range: tuple[float, float] | None = None


def compute_graph_ranges_for_width(width: SizeMM, start_time: int, end_time: int) -> GraphRanges:
    graph_offcut_width = 20.0
    mm_per_step = 0.5

    available_width = width - graph_offcut_width
    number_of_steps = int(available_width / mm_per_step)
    step = int((end_time - start_time) / number_of_steps / 2)
    return GraphRanges(time_range=(start_time, end_time), step=step)
