#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field, parse_obj_as

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

from cmk.gui.type_defs import SingleInfos, UnitInfo, VisualContext

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


@dataclass(frozen=True)
class RPNExpressionMetric:
    value: float
    unit_info: UnitInfo
    color: str


@dataclass(frozen=True)
class RPNExpressionConstant:
    value: float

    @property
    def ident(self) -> Literal["constant"]:
        return "constant"


@dataclass(frozen=True)
class RPNExpressionScalar:
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    scalar_name: Literal["warn", "crit", "min", "max"] | None

    @property
    def ident(self) -> Literal["scalar"]:
        return "scalar"


@dataclass(frozen=True)
class RPNExpressionOperator:
    operator_name: Literal["+", "*", "-", "/", "MAX", "MIN", "AVERAGE", "MERGE"]
    _operands: list[RPNExpression] = field(default_factory=list)

    @property
    def ident(self) -> Literal["operator"]:
        return "operator"

    @property
    def operands(self) -> Sequence[RPNExpression]:
        return self._operands

    def add_operands(self, operands: Sequence[RPNExpression]) -> None:
        self._operands.extend(operands)


@dataclass(frozen=True)
class RPNExpressionRRDChoice:
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None

    @property
    def ident(self) -> Literal["rrd_choice"]:
        return "rrd_choice"


@dataclass(frozen=True)
class RPNExpressionRRD:
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None
    scale: float

    @property
    def ident(self) -> Literal["rrd"]:
        return "rrd"


# TODO transformation is not part of cre but we first have to fix all types
@dataclass(frozen=True)
class RPNExpressionTransformation:
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
    _operands: list[RPNExpression] = field(default_factory=list)

    @property
    def ident(self) -> Literal["transformation"]:
        return "transformation"

    @property
    def mode(self) -> Literal["percentile", "forecast"]:
        return self.parameters[0]

    @property
    def operands(self) -> Sequence[RPNExpression]:
        return self._operands


# TODO Check: Similar to CombinedSingleMetricSpec
class SingleMetricSpec(TypedDict):
    datasource: str
    context: VisualContext
    selected_metric: tuple[str, LineType]
    consolidation_function: GraphConsoldiationFunction | None
    presentation: GraphPresentation
    single_infos: list[str]


# TODO combined is not part of cre but we first have to fix all types
@dataclass(frozen=True)
class RPNExpressionCombined:
    single_metric_spec: SingleMetricSpec

    @property
    def ident(self) -> Literal["combined"]:
        return "combined"


RPNExpression = (
    RPNExpressionConstant
    | RPNExpressionScalar
    | RPNExpressionOperator
    | RPNExpressionRRDChoice
    | RPNExpressionRRD
    | RPNExpressionTransformation
    | RPNExpressionCombined
)


class GraphMetric(BaseModel, frozen=True):
    title: str
    line_type: LineType
    expression: RPNExpression
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
