#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Annotated, final, Literal

from pydantic import (
    BaseModel,
    computed_field,
    Field,
    field_validator,
    PlainValidator,
    SerializeAsAny,
)

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

from cmk.gui.time_series import TimeSeries

from cmk.ccc.plugin_registry import Registry

from ._graph_render_config import GraphRenderOptions
from ._timeseries import AugmentedTimeSeries, derive_num_points_twindow, time_series_math
from ._type_defs import GraphConsolidationFunction, LineType, Operators, RRDData, RRDDataKey
from ._unit import ConvertibleUnitSpecification, NonConvertibleUnitSpecification


class HorizontalRule(BaseModel, frozen=True):
    value: float
    rendered_value: str
    color: str
    title: str


@dataclass(frozen=True)
class TranslationKey:
    host_name: HostName
    service_name: ServiceName


class MetricOperation(BaseModel, ABC, frozen=True):
    @staticmethod
    @abstractmethod
    def operation_name() -> str: ...

    @abstractmethod
    def keys(self) -> Iterator[TranslationKey | RRDDataKey]: ...

    @abstractmethod
    def compute_time_series(self, rrd_data: RRDData) -> Sequence[AugmentedTimeSeries]: ...

    def fade_odd_color(self) -> bool:
        return True

    # mypy does not support other decorators on top of @property:
    # https://github.com/python/mypy/issues/14461
    # https://docs.pydantic.dev/2.0/usage/computed_fields (mypy warning)
    @computed_field  # type: ignore[prop-decorator]
    @property
    @final
    def ident(self) -> str:
        return self.operation_name()


class MetricOperationRegistry(Registry[type[MetricOperation]]):
    def plugin_name(self, instance: type[MetricOperation]) -> str:
        return instance.operation_name()


metric_operation_registry = MetricOperationRegistry()


def parse_metric_operation(raw: object) -> MetricOperation:
    match raw:
        case MetricOperation():
            return raw
        case {"ident": str(ident), **rest}:
            return metric_operation_registry[ident].model_validate(rest)
        case dict():
            raise ValueError("Missing 'ident' key in metric operation")
    raise TypeError(raw)


class MetricOpConstant(MetricOperation, frozen=True):
    value: float

    @staticmethod
    def operation_name() -> Literal["constant"]:
        return "constant"

    def keys(self) -> Iterator[TranslationKey | RRDDataKey]:
        yield from ()

    def compute_time_series(self, rrd_data: RRDData) -> Sequence[AugmentedTimeSeries]:
        num_points, twindow = derive_num_points_twindow(rrd_data)
        return [AugmentedTimeSeries(data=TimeSeries([self.value] * num_points, twindow))]


class MetricOpConstantNA(MetricOperation, frozen=True):
    @staticmethod
    def operation_name() -> Literal["constant_na"]:
        return "constant_na"

    def keys(self) -> Iterator[TranslationKey | RRDDataKey]:
        yield from ()

    def compute_time_series(self, rrd_data: RRDData) -> Sequence[AugmentedTimeSeries]:
        num_points, twindow = derive_num_points_twindow(rrd_data)
        return [AugmentedTimeSeries(data=TimeSeries([None] * num_points, twindow))]


class MetricOpOperator(MetricOperation, frozen=True):
    operator_name: Operators
    operands: Sequence[
        Annotated[SerializeAsAny[MetricOperation], PlainValidator(parse_metric_operation)]
    ] = []

    @staticmethod
    def operation_name() -> Literal["operator"]:
        return "operator"

    def keys(self) -> Iterator[TranslationKey | RRDDataKey]:
        yield from (k for o in self.operands for k in o.keys())

    def compute_time_series(self, rrd_data: RRDData) -> Sequence[AugmentedTimeSeries]:
        if result := time_series_math(
            self.operator_name,
            [
                operand_evaluated.data
                for operand_evaluated in chain.from_iterable(
                    operand.compute_time_series(rrd_data) for operand in self.operands
                )
            ],
        ):
            return [AugmentedTimeSeries(data=result)]
        return []


class MetricOpRRDSource(MetricOperation, frozen=True):
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsolidationFunction | None
    scale: float

    @staticmethod
    def operation_name() -> Literal["rrd"]:
        return "rrd"

    def keys(self) -> Iterator[TranslationKey | RRDDataKey]:
        yield RRDDataKey(
            self.site_id,
            self.host_name,
            self.service_name,
            self.metric_name,
            self.consolidation_func_name,
            self.scale,
        )

    def compute_time_series(self, rrd_data: RRDData) -> Sequence[AugmentedTimeSeries]:
        if (
            key := RRDDataKey(
                self.site_id,
                self.host_name,
                self.service_name,
                self.metric_name,
                self.consolidation_func_name,
                self.scale,
            )
        ) in rrd_data:
            return [AugmentedTimeSeries(data=rrd_data[key])]

        num_points, twindow = derive_num_points_twindow(rrd_data)
        return [AugmentedTimeSeries(data=TimeSeries([None] * num_points, twindow))]


MetricOpOperator.model_rebuild()


class GraphMetric(BaseModel, frozen=True):
    title: str
    line_type: LineType
    operation: Annotated[SerializeAsAny[MetricOperation], PlainValidator(parse_metric_operation)]
    unit: str
    color: str


class GraphSpecification(BaseModel, ABC, frozen=True):
    @staticmethod
    @abstractmethod
    def graph_type_name() -> str: ...

    @abstractmethod
    def recipes(self) -> Sequence[GraphRecipe]: ...

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
    unit: str
    unit_spec: ConvertibleUnitSpecification | NonConvertibleUnitSpecification | None = Field(
        default=None,
        discriminator="type",
    )
    explicit_vertical_range: FixedVerticalRange | MinimalVerticalRange | None
    horizontal_rules: Sequence[HorizontalRule]
    omit_zero_metrics: bool
    consolidation_function: GraphConsolidationFunction | None
    # TODO: Use Sequence once https://github.com/pydantic/pydantic/issues/9319 is resolved
    # Internal marker: pydantic-9319
    metrics: list[GraphMetric]
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
