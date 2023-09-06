#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field, parse_obj_as

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

from cmk.gui.type_defs import SingleInfos, VisualContext

GraphConsoldiationFunction = Literal["max", "min", "average"]
GraphPresentation = Literal["lines", "stacked", "sum", "average", "min", "max"]
HorizontalRule = tuple[float, str, str, str]
LineType = Literal["line", "area", "stack", "-line", "-area", "-stack"]
MetricExpression = str


@dataclass(frozen=True, kw_only=True)
class MetricDefinition:
    expression: MetricExpression
    line_type: LineType
    title: str = ""


class MetricOpConstant(BaseModel, frozen=True):
    value: float

    @property
    def ident(self) -> Literal["constant"]:
        return "constant"


class MetricOpScalar(BaseModel, frozen=True):
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    scalar_name: Literal["warn", "crit", "min", "max"] | None

    @property
    def ident(self) -> Literal["scalar"]:
        return "scalar"


class MetricOpOperator(BaseModel, frozen=True):
    operator_name: Literal["+", "*", "-", "/", "MAX", "MIN", "AVERAGE", "MERGE"]
    # TODO Should be a sequence
    operands: list[MetricOperation] = []

    @property
    def ident(self) -> Literal["operator"]:
        return "operator"


# TODO transformation is not part of cre but we first have to fix all types
class MetricOpTransformation(BaseModel, frozen=True):
    # "percentile", {"percentile": INT}
    # "forecast", {
    #     "past": ...,
    #     "future": ...,
    #     "changepoint_prior_scale": CHOICE::[0.001, 0.01, 0.05, 0.1, 0.2,],
    #     "seasonality_mode": CHOICE::["additive", "multiplicative"],
    #     ""interval_width: CHOICE::[0.68, 0.86, 0.95],
    #     "display_past": INT,
    #     "display_model_parametrization": CHECKBOX,  # TODO
    # }
    # TODO Check params
    parameters: tuple[Literal["percentile"], float] | tuple[
        Literal["forecast"], Mapping[str, object]
    ]
    operands: Sequence[MetricOperation]

    @property
    def ident(self) -> Literal["transformation"]:
        return "transformation"

    @property
    def mode(self) -> Literal["percentile", "forecast"]:
        return self.parameters[0]


# TODO Check: Similar to CombinedSingleMetricSpec
class SingleMetricSpec(TypedDict):
    datasource: str
    context: VisualContext
    selected_metric: tuple[str, LineType]
    consolidation_function: GraphConsoldiationFunction | None
    presentation: GraphPresentation
    single_infos: list[str]


# TODO combined is not part of cre but we first have to fix all types
class MetricOpCombined(BaseModel, frozen=True):
    single_metric_spec: SingleMetricSpec

    @property
    def ident(self) -> Literal["combined"]:
        return "combined"


class MetricOpRRDSource(BaseModel, frozen=True):
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None
    scale: float

    @property
    def ident(self) -> Literal["rrd"]:
        return "rrd"


class MetricOpRRDChoice(BaseModel, frozen=True):
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None

    @property
    def ident(self) -> Literal["rrd_choice"]:
        return "rrd_choice"


MetricOperation = (
    MetricOpConstant
    | MetricOpOperator
    | MetricOpTransformation
    | MetricOpCombined
    # -----------------------------------------------------------------------------------------
    # The order of RRDSource and RRDChoice is very important for pydantic deserialization!!!
    # RRDChoice has a subset of attributes of RRDSource and is - more or less - an intermediate
    # step. pydantic uses the first matching object.
    | MetricOpRRDSource
    | MetricOpRRDChoice
    | MetricOpScalar
    # -----------------------------------------------------------------------------------------
)


MetricOpOperator.update_forward_refs()
MetricOpTransformation.update_forward_refs()


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
