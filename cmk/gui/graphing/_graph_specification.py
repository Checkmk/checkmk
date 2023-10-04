#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, Field, parse_obj_as
from typing_extensions import TypedDict

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

from cmk.gui.type_defs import SingleInfos, VisualContext

from ._type_defs import GraphConsoldiationFunction, GraphPresentation, LineType, Operators

HorizontalRule = tuple[float, str, str, str]


@dataclass(frozen=True, kw_only=True)
class MetricDefinition:
    expression: str
    line_type: LineType
    title: str = ""


class MetricOpConstant(BaseModel, frozen=True):
    ident: Literal["constant"] = "constant"
    value: float


class MetricOpScalar(BaseModel, frozen=True):
    ident: Literal["scalar"] = "scalar"
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    scalar_name: Literal["warn", "crit", "min", "max"] | None


class MetricOpOperator(BaseModel, frozen=True):
    ident: Literal["operator"] = "operator"
    operator_name: Operators
    operands: Sequence[MetricOperation] = []


class TransformationParametersPercentile(BaseModel, frozen=True):
    percentile: int


class TransformationParametersForecast(BaseModel, frozen=True):
    past: (
        Literal["m1", "m3", "m6", "y0", "y1"]
        | tuple[Literal["age"], int]
        | tuple[Literal["date"], tuple[float, float]]
    )
    future: (
        Literal["m-1", "m-3", "m-6", "y-1"]
        | tuple[Literal["next"], int]
        | tuple[Literal["until"], float]
    )
    changepoint_prior_scale: Literal["0.001", "0.01", "0.05", "0.1", "0.2"]
    seasonality_mode: Literal["additive", "multiplicative"]
    interval_width: Literal["0.68", "0.86", "0.95"]
    display_past: int
    display_model_parametrization: bool


# TODO transformation is not part of cre but we first have to fix all types
class MetricOpTransformation(BaseModel, frozen=True):
    ident: Literal["transformation"] = "transformation"
    parameters: TransformationParametersPercentile | TransformationParametersForecast
    operands: Sequence[MetricOperation]


# TODO Check: Similar to CombinedSingleMetricSpec
class SingleMetricSpec(TypedDict):
    datasource: str
    context: VisualContext
    selected_metric: MetricDefinition
    consolidation_function: GraphConsoldiationFunction | None
    presentation: GraphPresentation
    single_infos: list[str]


# TODO combined is not part of cre but we first have to fix all types
class MetricOpCombined(BaseModel, frozen=True):
    ident: Literal["combined"] = "combined"
    single_metric_spec: SingleMetricSpec


class MetricOpRRDSource(BaseModel, frozen=True):
    ident: Literal["rrd"] = "rrd"
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None
    scale: float


class MetricOpRRDChoice(BaseModel, frozen=True):
    ident: Literal["rrd_choice"] = "rrd_choice"
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None


MetricOperation = (
    MetricOpConstant
    | MetricOpOperator
    | MetricOpTransformation
    | MetricOpCombined
    | MetricOpRRDSource
    | MetricOpRRDChoice
    | MetricOpScalar
)


MetricOpOperator.model_rebuild()
MetricOpTransformation.model_rebuild()


class GraphMetric(BaseModel, frozen=True):
    title: str
    line_type: LineType
    expression: MetricOperation
    unit: str
    color: str
    visible: bool


class TemplateGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["template"] = "template"
    site: SiteId | None
    host_name: HostName
    service_description: ServiceName
    graph_index: int | None = None
    graph_id: str | None = None
    destination: str | None = None


class CombinedGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["combined"] = "combined"
    datasource: str
    single_infos: SingleInfos
    presentation: GraphPresentation
    context: VisualContext
    graph_template: str
    selected_metric: MetricDefinition | None = None
    consolidation_function: GraphConsoldiationFunction | None = None
    destination: str | None = None


class CustomGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["custom"] = "custom"
    id: str


class ExplicitGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["explicit"] = "explicit"
    title: str
    unit: str
    consolidation_function: GraphConsoldiationFunction | None
    explicit_vertical_range: tuple[float | None, float | None]
    omit_zero_metrics: bool
    horizontal_rules: Sequence[HorizontalRule]
    metrics: Sequence[GraphMetric]
    mark_requested_end_time: bool = False


class SingleTimeseriesGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["single_timeseries"] = "single_timeseries"
    site: SiteId
    metric: MetricName
    host: HostName | None = None
    service: ServiceName | None = None
    service_description: ServiceName | None = None
    color: str | None = None


class ForecastGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["forecast"] = "forecast"
    id: str
    destination: str | None = None


GraphSpecification = Annotated[
    (
        TemplateGraphSpecification
        | CombinedGraphSpecification
        | CustomGraphSpecification
        | ExplicitGraphSpecification
        | SingleTimeseriesGraphSpecification
        | ForecastGraphSpecification
    ),
    Field(discriminator="graph_type"),
]


def parse_raw_graph_specification(raw: Mapping[str, object]) -> GraphSpecification:
    # See https://github.com/pydantic/pydantic/issues/1847 and the linked mypy issue for the
    # suppressions below
    return parse_obj_as(GraphSpecification, raw)  # type: ignore[arg-type]
