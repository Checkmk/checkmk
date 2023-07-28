#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, Field, parse_obj_as

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

from cmk.gui.type_defs import (
    CombinedGraphSpec,
    ExplicitGraphSpec,
    GraphConsoldiationFunction,
    GraphMetric,
    GraphPresentation,
    HorizontalRule,
    MetricDefinitionWithoutTitle,
    SingleInfos,
    SingleTimeseriesGraphSpec,
    TemplateGraphSpec,
    VisualContext,
)


class TemplateGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["template"] = "template"
    site: SiteId | None
    host_name: HostName
    service_description: ServiceName
    graph_index: int | None = None
    graph_id: str | None = None
    destination: str | None = None

    def to_legacy_format(self) -> TemplateGraphSpec:
        return TemplateGraphSpec(
            site=self.site,
            host_name=self.host_name,
            service_description=self.service_description,
            graph_index=self.graph_index,
            graph_id=self.graph_id,
        )


class CombinedGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["combined"] = "combined"
    datasource: str
    single_infos: SingleInfos
    presentation: GraphPresentation
    context: VisualContext
    graph_template: str
    selected_metric: MetricDefinitionWithoutTitle | None = None
    consolidation_function: GraphConsoldiationFunction | None = None
    destination: str | None = None

    def to_legacy_format(self) -> CombinedGraphSpec:
        legacy_spec = CombinedGraphSpec(
            datasource=self.datasource,
            single_infos=self.single_infos,
            presentation=self.presentation,
            context=self.context,
            graph_template=self.graph_template,
        )
        if self.selected_metric:
            legacy_spec["selected_metric"] = self.selected_metric
        if self.consolidation_function:
            legacy_spec["consolidation_function"] = self.consolidation_function
        return legacy_spec


class CustomGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["custom"] = "custom"
    id: str

    def to_legacy_format(self) -> str:
        return self.id


class ExplicitGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["explicit"] = "explicit"
    title: str
    unit: str
    consolidation_function: GraphConsoldiationFunction | None
    explicit_vertical_range: tuple[float | None, float | None]
    omit_zero_metrics: bool
    horizontal_rules: Sequence[HorizontalRule]
    metrics: Sequence[GraphMetric]

    def to_legacy_format(self) -> ExplicitGraphSpec:
        return ExplicitGraphSpec(
            title=self.title,
            unit=self.unit,
            consolidation_function=self.consolidation_function,
            explicit_vertical_range=self.explicit_vertical_range,
            omit_zero_metrics=self.omit_zero_metrics,
            horizontal_rules=self.horizontal_rules,
            metrics=self.metrics,
        )


class SingleTimeseriesGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["single_timeseries"] = "single_timeseries"
    site: SiteId
    metric: MetricName
    host: HostName | None = None
    service: ServiceName | None = None
    service_description: ServiceName | None = None
    color: str | None = None

    def to_legacy_format(self) -> SingleTimeseriesGraphSpec:
        legacy_spec = SingleTimeseriesGraphSpec(
            site=self.site,
            metric=self.metric,
            color=self.color,
        )
        if self.host:
            legacy_spec["host"] = self.host
        if self.service:
            legacy_spec["service"] = self.service
        if self.service_description:
            legacy_spec["service_description"] = self.service_description
        return legacy_spec


class ForecastGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["forecast"] = "forecast"
    id: str
    destination: str | None = None

    def to_legacy_format(self) -> str:
        return self.id


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
