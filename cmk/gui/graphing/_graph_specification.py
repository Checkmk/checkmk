#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Callable, Literal, Self, Union

from pydantic import BaseModel, Field, field_validator, SerializeAsAny, TypeAdapter
from typing_extensions import TypedDict

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.plugin_registry import Registry
from cmk.utils.servicename import ServiceName

from cmk.gui.type_defs import VisualContext

from ._graph_render_config import GraphRenderOptions
from ._type_defs import (
    GraphConsoldiationFunction,
    GraphPresentation,
    LineType,
    Operators,
    TranslatedMetric,
)

HorizontalRule = tuple[float, str, str, str]


class SelectedMetric(BaseModel, frozen=True):
    expression: str
    line_type: LineType


@dataclass(frozen=True)
class CombinedSingleMetricSpec:
    datasource: str
    context: VisualContext
    selected_metric: SelectedMetric
    consolidation_function: GraphConsoldiationFunction
    presentation: GraphPresentation


@dataclass(frozen=True)
class NeededElementForTranslation:
    host_name: HostName
    service_name: ServiceName


@dataclass(frozen=True)
class NeededElementForRRDDataKey:
    # TODO Intermediate step, will be cleaned up:
    # Relates to MetricOperation::rrd with SiteId, etc.
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: str
    consolidation_func_name: GraphConsoldiationFunction | None
    scale: float


RetranslationMap = Mapping[
    tuple[HostName, ServiceName], Mapping[MetricName, tuple[SiteId, TranslatedMetric]]
]


class MetricOpConstant(BaseModel, frozen=True):
    ident: Literal["constant"] = "constant"
    value: float

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        yield from ()

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        return self


class MetricOpScalar(BaseModel, frozen=True):
    ident: Literal["scalar"] = "scalar"
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    scalar_name: Literal["warn", "crit", "min", "max"] | None

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        yield NeededElementForTranslation(self.host_name, self.service_name)

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        _site, trans = retranslation_map[(self.host_name, self.service_name)][self.metric_name]
        if not isinstance(value := trans["scalar"].get(str(self.scalar_name)), float):
            # TODO if scalar_name not in trans["scalar"] -> crash; No warning to the user :(
            raise TypeError(value)
        return MetricOpConstant(value=value)


class MetricOpOperator(BaseModel, frozen=True):
    ident: Literal["operator"] = "operator"
    operator_name: Operators
    operands: Sequence[MetricOperation] = []

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        yield from (
            ne
            for o in self.operands
            for ne in o.needed_elements(resolve_combined_single_metric_spec)
        )

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        return MetricOpOperator(
            operator_name=self.operator_name,
            operands=[o.reverse_translate(retranslation_map) for o in self.operands],
        )


class TransformationParametersPercentile(BaseModel, frozen=True):
    percentile: int


class VSTransformationParametersForecast(TypedDict):
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
    changepoint_prior_scale: float
    seasonality_mode: Literal["additive", "multiplicative"]
    interval_width: float
    display_past: int
    display_model_parametrization: bool


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

    @classmethod
    def from_vs_parameters(cls, vs_params: VSTransformationParametersForecast) -> Self:
        return cls(
            past=vs_params["past"],
            future=vs_params["future"],
            changepoint_prior_scale=cls._parse_changepoint_prior_scale(
                vs_params["changepoint_prior_scale"]
            ),
            seasonality_mode=vs_params["seasonality_mode"],
            interval_width=cls._parse_interval_width(vs_params["interval_width"]),
            display_past=vs_params["display_past"],
            display_model_parametrization=vs_params["display_model_parametrization"],
        )

    def to_vs_parameters(self) -> VSTransformationParametersForecast:
        return VSTransformationParametersForecast(
            past=self.past,
            future=self.future,
            changepoint_prior_scale=float(self.changepoint_prior_scale),
            seasonality_mode=self.seasonality_mode,
            interval_width=float(self.interval_width),
            display_past=self.display_past,
            display_model_parametrization=self.display_model_parametrization,
        )

    @staticmethod
    def _parse_changepoint_prior_scale(
        raw: float,
    ) -> Literal["0.001", "0.01", "0.05", "0.1", "0.2"]:
        match raw:
            case 0.001:
                return "0.001"
            case 0.01:
                return "0.01"
            case 0.05:
                return "0.05"
            case 0.1:
                return "0.1"
            case 0.2:
                return "0.2"
        raise ValueError(raw)

    @staticmethod
    def _parse_interval_width(
        raw: float,
    ) -> Literal["0.68", "0.86", "0.95"]:
        match raw:
            case 0.68:
                return "0.68"
            case 0.86:
                return "0.86"
            case 0.95:
                return "0.95"
        raise ValueError(raw)


# TODO transformation is not part of cre but we first have to fix all types
class MetricOpTransformation(BaseModel, frozen=True):
    ident: Literal["transformation"] = "transformation"
    parameters: TransformationParametersPercentile | TransformationParametersForecast
    operands: Sequence[MetricOperation]

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        yield from (
            ne
            for o in self.operands
            for ne in o.needed_elements(resolve_combined_single_metric_spec)
        )

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        return MetricOpTransformation(
            parameters=self.parameters,
            operands=[o.reverse_translate(retranslation_map) for o in self.operands],
        )


# TODO Check: Similar to CombinedSingleMetricSpec
class SingleMetricSpec(TypedDict):
    datasource: str
    context: VisualContext
    selected_metric: SelectedMetric
    consolidation_function: GraphConsoldiationFunction | None
    presentation: GraphPresentation
    single_infos: list[str]


# TODO combined is not part of cre but we first have to fix all types
class MetricOpCombined(BaseModel, frozen=True):
    ident: Literal["combined"] = "combined"
    single_metric_spec: SingleMetricSpec

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        if (consolidation_func_name := self.single_metric_spec["consolidation_function"]) is None:
            raise TypeError(consolidation_func_name)

        for metric in resolve_combined_single_metric_spec(
            CombinedSingleMetricSpec(
                datasource=self.single_metric_spec["datasource"],
                context=self.single_metric_spec["context"],
                selected_metric=self.single_metric_spec["selected_metric"],
                consolidation_function=consolidation_func_name,
                presentation=self.single_metric_spec["presentation"],
            )
        ):
            yield from metric.operation.needed_elements(resolve_combined_single_metric_spec)

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        return self


class MetricOpRRDSource(BaseModel, frozen=True):
    ident: Literal["rrd"] = "rrd"
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None
    scale: float

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        yield NeededElementForRRDDataKey(
            self.site_id,
            self.host_name,
            self.service_name,
            self.metric_name,
            self.consolidation_func_name,
            self.scale,
        )

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        site_id, trans = retranslation_map[(self.host_name, self.service_name)][self.metric_name]
        metrics: list[MetricOperation] = [
            MetricOpRRDSource(
                site_id=site_id,
                host_name=self.host_name,
                service_name=self.service_name,
                metric_name=name,
                consolidation_func_name=self.consolidation_func_name,
                scale=scale,
            )
            for name, scale in zip(trans["orig_name"], trans["scale"])
        ]

        if len(metrics) > 1:
            return MetricOpOperator(operator_name="MERGE", operands=metrics)

        return metrics[0]


class MetricOpRRDChoice(BaseModel, frozen=True):
    ident: Literal["rrd_choice"] = "rrd_choice"
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        yield NeededElementForTranslation(self.host_name, self.service_name)

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        site_id, trans = retranslation_map[(self.host_name, self.service_name)][self.metric_name]
        metrics: list[MetricOperation] = [
            MetricOpRRDSource(
                site_id=site_id,
                host_name=self.host_name,
                service_name=self.service_name,
                metric_name=name,
                consolidation_func_name=self.consolidation_func_name,
                scale=scale,
            )
            for name, scale in zip(trans["orig_name"], trans["scale"])
        ]

        if len(metrics) > 1:
            return MetricOpOperator(operator_name="MERGE", operands=metrics)

        return metrics[0]


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
    operation: MetricOperation
    unit: str
    color: str
    visible: bool


class GraphSpecification(BaseModel, ABC, frozen=True):
    graph_type: str

    @staticmethod
    @abstractmethod
    def name() -> str:
        ...

    @abstractmethod
    def recipes(self) -> Sequence[GraphRecipe]:
        ...


class GraphSpecificationRegistry(Registry[type[GraphSpecification]]):
    def plugin_name(self, instance: type[GraphSpecification]) -> str:
        return instance.name()


graph_specification_registry = GraphSpecificationRegistry()


def parse_raw_graph_specification(raw: Mapping[str, object]) -> GraphSpecification:
    parsed = TypeAdapter(
        Annotated[
            Union[*graph_specification_registry.values()],
            Field(discriminator="graph_type"),
        ],
    ).validate_python(raw)
    # mypy apparently doesn't understand TypeAdapter.validate_python
    assert isinstance(parsed, GraphSpecification)
    return parsed


class GraphDataRange(BaseModel, frozen=True):
    time_range: tuple[int, int]
    # Forecast graphs represent step as str (see forecasts.py and fetch_rrd_data)
    # colon separated [step length]:[rrd point count]
    step: int | str
    vertical_range: tuple[float, float] | None = None


class AdditionalGraphHTML(BaseModel, frozen=True):
    title: str
    html: str


class GraphRecipeBase(BaseModel, frozen=True):
    title: str
    unit: str
    explicit_vertical_range: tuple[float | None, float | None]
    horizontal_rules: Sequence[HorizontalRule]
    omit_zero_metrics: bool
    consolidation_function: GraphConsoldiationFunction | None
    metrics: Sequence[GraphMetric]
    additional_html: AdditionalGraphHTML | None = None
    render_options: GraphRenderOptions = GraphRenderOptions()
    data_range: GraphDataRange | None = None
    mark_requested_end_time: bool = False


class GraphRecipe(GraphRecipeBase, frozen=True):
    # https://docs.pydantic.dev/2.4/concepts/serialization/#subclass-instances-for-fields-of-basemodel-dataclasses-typeddict
    # https://docs.pydantic.dev/2.4/concepts/serialization/#serializing-with-duck-typing
    specification: SerializeAsAny[GraphSpecification]

    @field_validator("specification", mode="before")
    def parse_specification(cls, value: Mapping[str, object]) -> GraphSpecification:
        return parse_raw_graph_specification(value)
