#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

from __future__ import annotations

import functools
import operator
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Annotated, assert_never, final, Literal, TypeVar

from pydantic import BaseModel, computed_field, PlainValidator, SerializeAsAny

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import SiteId
from cmk.gui.i18n import _
from cmk.gui.utils import escaping
from cmk.utils.metrics import MetricName
from cmk.utils.misc import pnp_cleanup
from cmk.utils.servicename import ServiceName

from ._from_api import RegisteredMetric
from ._time_series import TimeSeries, TimeSeriesValues
from ._translated_metrics import TranslatedMetric

GraphConsolidationFunction = Literal["max", "min", "average"]
LineType = Literal["line", "area", "stack", "-line", "-area", "-stack"]


def create_graph_metric_expression_from_translated_metric(
    site_id: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    translated_metric: TranslatedMetric,
    consolidation_function: GraphConsolidationFunction | None,
) -> GraphMetricRRDSource | GraphMetricOperation:
    metrics = [
        GraphMetricRRDSource(
            site_id=site_id,
            host_name=host_name,
            service_name=service_name,
            metric_name=pnp_cleanup(o.name),
            consolidation_func_name=consolidation_function,
            scale=o.scale,
        )
        for o in translated_metric.originals
    ]
    if len(metrics) > 1:
        return GraphMetricOperation(operator_name="MERGE", operands=metrics)
    return metrics[0]


def line_type_mirror(line_type: LineType) -> LineType:
    match line_type:
        case "line":
            return "-line"
        case "-line":
            return "line"
        case "area":
            return "-area"
        case "-area":
            return "area"
        case "stack":
            return "-stack"
        case "-stack":
            return "stack"
        case other:
            assert_never(other)


Operators = Literal["+", "*", "-", "/", "MAX", "MIN", "AVERAGE", "MERGE"]


@dataclass(frozen=True)
class TranslationKey:
    host_name: HostName
    service_name: ServiceName


@dataclass(frozen=True)
class RRDDataKey:
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: str
    consolidation_function: GraphConsolidationFunction | None
    scale: float


@dataclass(frozen=True)
class GraphLineQueryAttribute:
    key: str
    value: str


@dataclass(frozen=True)
class QueryDataKey:
    metric_name: MetricName
    resource_attributes: tuple[GraphLineQueryAttribute, ...]
    scope_attributes: tuple[GraphLineQueryAttribute, ...]
    data_point_attributes: tuple[GraphLineQueryAttribute, ...]
    aggregation_lookback: float
    aggregation_histogram_percentile: float


@dataclass(frozen=True)
class QueryDataValue:
    metric_type: Literal["gauge", "sum", "histogram", "exponential_histogram", "summary"]
    time_series: TimeSeries
    id: str
    attributes: Mapping[Literal["resource", "scope", "data_point"], Mapping[str, str]]


type RRDData = Mapping[RRDDataKey, TimeSeries]
type QueryData = Mapping[QueryDataKey, Sequence[QueryDataValue]]


def _derive_num_points(rrd_data: RRDData) -> tuple[int, int, int, int]:
    if rrd_data:
        sample_data = next(iter(rrd_data.values()))
        return len(sample_data), sample_data.start, sample_data.end, sample_data.step
    # no data, default clean graph, use for pure scalars on custom graphs
    return 1, 0, 60, 60


_TOperatorReturn = TypeVar("_TOperatorReturn")


def op_func_wrapper(
    op_func: Callable[[TimeSeries | TimeSeriesValues], _TOperatorReturn],
    tsp: TimeSeries | TimeSeriesValues,
) -> _TOperatorReturn | None:
    if tsp.count(None) < len(tsp):  # At least one non-None value
        try:
            return op_func(tsp)
        except ZeroDivisionError:
            pass
    return None


def clean_time_series_point(tsp: TimeSeries | TimeSeriesValues) -> list[float]:
    """removes "None" entries from input list"""
    return [x for x in tsp if x is not None]


def _time_series_operator_sum(tsp: TimeSeries | TimeSeriesValues) -> float:
    return sum(clean_time_series_point(tsp))


def _time_series_operator_product(tsp: TimeSeries | TimeSeriesValues) -> float | None:
    if None in tsp:
        return None
    return functools.reduce(operator.mul, tsp, 1)


def _time_series_operator_difference(tsp: TimeSeries | TimeSeriesValues) -> float | None:
    if None in tsp:
        return None
    assert tsp[0] is not None
    assert tsp[1] is not None
    return tsp[0] - tsp[1]


def _time_series_operator_fraction(tsp: TimeSeries | TimeSeriesValues) -> float | None:
    if None in tsp or tsp[1] == 0:
        return None
    assert tsp[0] is not None
    assert tsp[1] is not None
    return tsp[0] / tsp[1]


def _time_series_operator_maximum(tsp: TimeSeries | TimeSeriesValues) -> float:
    return max(clean_time_series_point(tsp))


def _time_series_operator_minimum(tsp: TimeSeries | TimeSeriesValues) -> float:
    return min(clean_time_series_point(tsp))


def _time_series_operator_average(tsp: TimeSeries | TimeSeriesValues) -> float:
    tsp_clean = clean_time_series_point(tsp)
    return sum(tsp_clean) / len(tsp_clean)


def time_series_operators() -> dict[
    Operators,
    tuple[str, Callable[[TimeSeries | TimeSeriesValues], float | None]],
]:
    return {
        "+": (_("Sum"), _time_series_operator_sum),
        "*": (_("Product"), _time_series_operator_product),
        "-": (_("Difference"), _time_series_operator_difference),
        "/": (_("Fraction"), _time_series_operator_fraction),
        "MAX": (_("Maximum"), _time_series_operator_maximum),
        "MIN": (_("Minimum"), _time_series_operator_minimum),
        "AVERAGE": (_("Average"), _time_series_operator_average),
        "MERGE": ("First not None", lambda x: next(iter(clean_time_series_point(x)))),
    }


@dataclass(frozen=True, kw_only=True)
class TimeSeriesMetaData:
    title: str | None
    line_type: LineType | Literal["ref"] | None
    color: str | None
    attributes: Mapping[Literal["resource", "scope", "data_point"], Mapping[str, str]]
    metric_name: str | None = None


@dataclass(frozen=True)
class AugmentedTimeSeries:
    time_series: TimeSeries
    meta_data: TimeSeriesMetaData | None = None


class GraphMetricExpression(BaseModel, ABC, frozen=True):
    @staticmethod
    @abstractmethod
    def expression_name() -> str: ...

    @abstractmethod
    def keys(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
    ) -> Iterator[TranslationKey | RRDDataKey | QueryDataKey]: ...

    @abstractmethod
    def compute_augmented_time_series(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        rrd_data: RRDData,
        query_data: QueryData,
    ) -> Sequence[AugmentedTimeSeries]: ...

    def fade_odd_color(self) -> bool:
        return True

    # mypy does not support other decorators on top of @property:
    # https://github.com/python/mypy/issues/14461
    # https://docs.pydantic.dev/2.0/usage/computed_fields (mypy warning)
    @computed_field  # type: ignore[prop-decorator]
    @property
    @final
    def ident(self) -> str:
        return self.expression_name()


class GraphMetricExpressionRegistry(Registry[type[GraphMetricExpression]]):
    def plugin_name(self, instance: type[GraphMetricExpression]) -> str:
        return instance.expression_name()


graph_metric_expression_registry = GraphMetricExpressionRegistry()


def parse_graph_metric_expression(raw: object) -> GraphMetricExpression:
    match raw:
        case GraphMetricExpression():
            return raw
        case {"ident": str(ident), **rest}:
            return graph_metric_expression_registry[ident].model_validate(rest)
        case dict():
            raise ValueError("Missing 'ident' key in metric operation")
    raise TypeError(raw)


class GraphMetricConstant(GraphMetricExpression, frozen=True):
    value: float

    @staticmethod
    def expression_name() -> Literal["constant"]:
        return "constant"

    def keys(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
    ) -> Iterator[TranslationKey | RRDDataKey | QueryDataKey]:
        yield from ()

    def compute_augmented_time_series(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        rrd_data: RRDData,
        query_data: QueryData,
    ) -> Sequence[AugmentedTimeSeries]:
        num_points, start, end, step = _derive_num_points(rrd_data)
        return [
            AugmentedTimeSeries(
                time_series=TimeSeries(
                    start=start,
                    end=end,
                    step=step,
                    values=[self.value] * num_points,
                )
            )
        ]


class GraphMetricConstantNA(GraphMetricExpression, frozen=True):
    @staticmethod
    def expression_name() -> Literal["constant_na"]:
        return "constant_na"

    def keys(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
    ) -> Iterator[TranslationKey | RRDDataKey | QueryDataKey]:
        yield from ()

    def compute_augmented_time_series(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        rrd_data: RRDData,
        query_data: QueryData,
    ) -> Sequence[AugmentedTimeSeries]:
        num_points, start, end, step = _derive_num_points(rrd_data)
        return [
            AugmentedTimeSeries(
                time_series=TimeSeries(
                    start=start,
                    end=end,
                    step=step,
                    values=[None] * num_points,
                )
            )
        ]


def _time_series_math(
    operator_id: Operators,
    operands_evaluated: list[TimeSeries],
) -> TimeSeries | None:
    operators = time_series_operators()
    if operator_id not in operators:
        raise MKGeneralException(
            _("Undefined operator '%s' in graph expression")
            % escaping.escape_attribute(operator_id)
        )
    # Test for correct arity on FOUND[evaluated] data
    if any(
        (
            operator_id in ["-", "/"] and len(operands_evaluated) != 2,
            len(operands_evaluated) < 1,
        )
    ):
        # raise MKGeneralException(_("Incorrect amount of data to correctly evaluate expression"))
        # Silently return so to get an empty graph slot
        return None

    _op_title, op_func = operators[operator_id]
    time_series = operands_evaluated[0]
    return TimeSeries(
        start=time_series.start,
        end=time_series.end,
        step=time_series.step,
        values=[op_func_wrapper(op_func, list(tsp)) for tsp in zip(*operands_evaluated)],
    )


class GraphMetricOperation(GraphMetricExpression, frozen=True):
    operator_name: Operators
    operands: Sequence[
        Annotated[
            SerializeAsAny[GraphMetricExpression], PlainValidator(parse_graph_metric_expression)
        ]
    ] = []

    @staticmethod
    def expression_name() -> Literal["operator"]:
        return "operator"

    def keys(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
    ) -> Iterator[TranslationKey | RRDDataKey | QueryDataKey]:
        yield from (k for o in self.operands for k in o.keys(registered_metrics))

    def compute_augmented_time_series(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        rrd_data: RRDData,
        query_data: QueryData,
    ) -> Sequence[AugmentedTimeSeries]:
        if result := _time_series_math(
            self.operator_name,
            [
                operand_evaluated.time_series
                for operand_evaluated in chain.from_iterable(
                    operand.compute_augmented_time_series(registered_metrics, rrd_data, query_data)
                    for operand in self.operands
                )
            ],
        ):
            return [AugmentedTimeSeries(time_series=result)]
        return []


GraphMetricOperation.model_rebuild()


AnnotatedHostName = Annotated[HostName, PlainValidator(HostName.parse)]


class GraphMetricRRDSource(GraphMetricExpression, frozen=True):
    site_id: SiteId
    host_name: AnnotatedHostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsolidationFunction | None
    scale: float

    @staticmethod
    def expression_name() -> Literal["rrd"]:
        return "rrd"

    def keys(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
    ) -> Iterator[TranslationKey | RRDDataKey | QueryDataKey]:
        yield RRDDataKey(
            self.site_id,
            self.host_name,
            self.service_name,
            self.metric_name,
            self.consolidation_func_name,
            self.scale,
        )

    def compute_augmented_time_series(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        rrd_data: RRDData,
        query_data: QueryData,
    ) -> Sequence[AugmentedTimeSeries]:
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
            return [AugmentedTimeSeries(time_series=rrd_data[key])]

        num_points, start, end, step = _derive_num_points(rrd_data)
        return [
            AugmentedTimeSeries(
                time_series=TimeSeries(
                    start=start,
                    end=end,
                    step=step,
                    values=[None] * num_points,
                ),
            )
        ]
