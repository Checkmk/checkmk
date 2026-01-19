#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

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
from cmk.gui.color import Color
from cmk.gui.i18n import _
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.temperate_unit import TemperatureUnit

from ._from_api import RegisteredMetric
from ._graph_metric_expressions import (
    GraphConsolidationFunction,
    GraphMetricExpression,
    line_type_mirror,
    LineType,
    parse_graph_metric_expression,
)
from ._graph_render_config import GraphRenderOptions
from ._translated_metrics import TranslatedMetric
from ._unit import (
    ConvertibleUnitSpecification,
    NonConvertibleUnitSpecification,
    UserSpecificUnit,
)


class HorizontalRule(BaseModel, frozen=True):
    value: float
    rendered_value: str
    color: str
    title: str


def compute_warn_crit_rules_from_translated_metric(
    user_specific_unit: UserSpecificUnit,
    translated_metric: TranslatedMetric,
) -> Sequence[HorizontalRule]:
    horizontal_rules = []
    if (warn_value := translated_metric.scalar.get("warn")) is not None and warn_value not in (
        float("inf"),
        float("-inf"),
    ):
        horizontal_rules.append(
            HorizontalRule(
                value=warn_value,
                rendered_value=user_specific_unit.formatter.render(warn_value),
                color=Color.WARN.value,
                title=_("Warning"),
            )
        )
    if (crit_value := translated_metric.scalar.get("crit")) is not None and crit_value not in (
        float("inf"),
        float("-inf"),
    ):
        horizontal_rules.append(
            HorizontalRule(
                value=crit_value,
                rendered_value=user_specific_unit.formatter.render(crit_value),
                color=Color.CRIT.value,
                title=_("Critical"),
            )
        )
    return horizontal_rules


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
    @staticmethod
    @abstractmethod
    def graph_type_name() -> str: ...

    @abstractmethod
    def recipes(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
        user_permissions: UserPermissions,
        *,
        consolidation_function: GraphConsolidationFunction,
        debug: bool,
        temperature_unit: TemperatureUnit,
    ) -> Sequence[GraphRecipe]: ...

    # mypy does not support other decorators on top of @property:
    # https://github.com/python/mypy/issues/14461
    # https://docs.pydantic.dev/2.0/usage/computed_fields (mypy warning)
    @computed_field  # type: ignore[prop-decorator]
    @property
    @final
    def graph_type(self) -> str:
        return self.graph_type_name()

    def url(self) -> str:
        return ""


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
    @classmethod
    def parse_specification(cls, value: Mapping[str, object]) -> GraphSpecification:
        return parse_raw_graph_specification(value)
