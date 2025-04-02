#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Annotated, Literal, NamedTuple

from pydantic import BaseModel, field_validator, PlainValidator, SerializeAsAny

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.plugin_registry import Registry
from cmk.utils.servicename import ServiceName

from cmk.gui.time_series import TimeSeries

from ._graph_render_config import GraphRenderOptions
from ._timeseries import (
    AugmentedTimeSeries,
    derive_num_points_twindow,
    time_series_math,
)
from ._type_defs import (
    GraphConsoldiationFunction,
    LineType,
    Operators,
    RRDData,
    RRDDataKey,
)


class HorizontalRule(NamedTuple):
    value: float
    rendered_value: str
    color: str
    title: str


@dataclass(frozen=True)
class TranslationKey:
    host_name: HostName
    service_name: ServiceName


class MetricOperation(BaseModel, ABC, frozen=True):
    ident: str

    @staticmethod
    @abstractmethod
    def name() -> str:
        raise NotImplementedError()

    @abstractmethod
    def keys(self) -> Iterator[TranslationKey | RRDDataKey]:
        raise NotImplementedError()

    @abstractmethod
    def compute_time_series(self, rrd_data: RRDData) -> Sequence[AugmentedTimeSeries]:
        raise NotImplementedError()

    def fade_odd_color(self) -> bool:
        return True


class MetricOperationRegistry(Registry[type[MetricOperation]]):
    def plugin_name(self, instance: type[MetricOperation]) -> str:
        return instance.name()


metric_operation_registry = MetricOperationRegistry()


def parse_metric_operation(raw: object) -> MetricOperation:
    if isinstance(raw, MetricOperation):
        return raw
    if isinstance(raw, dict):
        return metric_operation_registry[f'metric_op_{raw["ident"]}'].model_validate(raw)
    raise TypeError(raw)


class MetricOpConstant(MetricOperation, frozen=True):
    ident: Literal["constant"] = "constant"
    value: float

    @staticmethod
    def name() -> str:
        return "metric_op_constant"

    def keys(self) -> Iterator[TranslationKey | RRDDataKey]:
        yield from ()

    def compute_time_series(self, rrd_data: RRDData) -> Sequence[AugmentedTimeSeries]:
        num_points, twindow = derive_num_points_twindow(rrd_data)
        return [AugmentedTimeSeries(data=TimeSeries([self.value] * num_points, twindow))]


class MetricOpConstantNA(MetricOperation, frozen=True):
    ident: Literal["constant_na"] = "constant_na"

    @staticmethod
    def name() -> str:
        return "metric_op_constant_na"

    def keys(self) -> Iterator[TranslationKey | RRDDataKey]:
        yield from ()

    def compute_time_series(self, rrd_data: RRDData) -> Sequence[AugmentedTimeSeries]:
        num_points, twindow = derive_num_points_twindow(rrd_data)
        return [AugmentedTimeSeries(data=TimeSeries([None] * num_points, twindow))]


class MetricOpOperator(MetricOperation, frozen=True):
    ident: Literal["operator"] = "operator"
    operator_name: Operators
    operands: Sequence[
        Annotated[SerializeAsAny[MetricOperation], PlainValidator(parse_metric_operation)]
    ] = []

    @staticmethod
    def name() -> str:
        return "metric_op_operator"

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
    ident: Literal["rrd"] = "rrd"
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None
    scale: float

    @staticmethod
    def name() -> str:
        return "metric_op_rrd"

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
    visible: bool


class GraphSpecification(BaseModel, ABC, frozen=True):
    graph_type: str

    @staticmethod
    @abstractmethod
    def name() -> str: ...

    @abstractmethod
    def recipes(self) -> Sequence[GraphRecipe]: ...


class GraphSpecificationRegistry(Registry[type[GraphSpecification]]):
    def plugin_name(self, instance: type[GraphSpecification]) -> str:
        return instance.name()


graph_specification_registry = GraphSpecificationRegistry()


def parse_raw_graph_specification(raw: object) -> GraphSpecification:
    if isinstance(raw, GraphSpecification):
        return raw
    if isinstance(raw, dict):
        return graph_specification_registry[
            f"{raw['graph_type']}_graph_specification"
        ].model_validate(raw)
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
    explicit_vertical_range: FixedVerticalRange | MinimalVerticalRange | None
    horizontal_rules: Sequence[HorizontalRule]
    omit_zero_metrics: bool
    consolidation_function: GraphConsoldiationFunction | None
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
