#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import functools
import json
import operator
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Annotated, assert_never, final, Literal, override

from pydantic import BaseModel, computed_field, PlainValidator, SerializeAsAny

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import SiteId
from cmk.gui.i18n import _
from cmk.utils.metrics import MetricName
from cmk.utils.misc import pnp_cleanup
from cmk.utils.servicename import ServiceName
from cmk.web.utils import escaping

from ._from_api import RegisteredMetric
from ._time_series import TimeSeries
from ._translated_metrics import TranslatedMetric

GraphConsolidationFunction = Literal["max", "min", "average"]
LineType = Literal["line", "area", "stack", "-line", "-area", "-stack"]
type DrawnLineType = Literal["line", "area", "stack"]
type AttributeGroup = Literal["resource", "scope", "data_point"]


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


@dataclass(frozen=True, kw_only=True)
class GraphLineGroupByKey:
    kind: AttributeGroup
    key: str


@dataclass(frozen=True, kw_only=True)
class GaugeLast:
    lookback_seconds: float
    type_: Literal["gauge_last"] = "gauge_last"


@dataclass(frozen=True, kw_only=True)
class GaugeMax:
    lookback_seconds: float
    type_: Literal["gauge_max"] = "gauge_max"


@dataclass(frozen=True, kw_only=True)
class GaugeAvg:
    lookback_seconds: float
    type_: Literal["gauge_avg"] = "gauge_avg"


@dataclass(frozen=True, kw_only=True)
class GaugeMin:
    lookback_seconds: float
    type_: Literal["gauge_min"] = "gauge_min"


@dataclass(frozen=True, kw_only=True)
class SumRate:
    lookback_seconds: float
    type_: Literal["sum_rate"] = "sum_rate"


@dataclass(frozen=True, kw_only=True)
class SumLastRaw:
    lookback_seconds: float
    type_: Literal["sum_last_raw"] = "sum_last_raw"


@dataclass(frozen=True, kw_only=True)
class SumDelta:
    lookback_seconds: float
    type_: Literal["sum_delta"] = "sum_delta"


@dataclass(frozen=True, kw_only=True)
class HistogramQuantile:
    lookback_seconds: float
    percentile: float
    type_: Literal["histogram_quantile"] = "histogram_quantile"


@dataclass(frozen=True, kw_only=True)
class HistogramCountDelta:
    lookback_seconds: float
    type_: Literal["histogram_count_delta"] = "histogram_count_delta"


@dataclass(frozen=True, kw_only=True)
class HistogramCountRate:
    lookback_seconds: float
    type_: Literal["histogram_count_rate"] = "histogram_count_rate"


@dataclass(frozen=True, kw_only=True)
class HistogramSumRate:
    lookback_seconds: float
    type_: Literal["histogram_sum_rate"] = "histogram_sum_rate"


@dataclass(frozen=True, kw_only=True)
class HistogramSumDelta:
    lookback_seconds: float
    type_: Literal["histogram_sum_delta"] = "histogram_sum_delta"


@dataclass(frozen=True, kw_only=True)
class HistogramSumRaw:
    lookback_seconds: float
    type_: Literal["histogram_sum_raw"] = "histogram_sum_raw"


@dataclass(frozen=True, kw_only=True)
class HistogramFractionBelow:
    lookback_seconds: float
    threshold: float
    type_: Literal["histogram_fraction_below"] = "histogram_fraction_below"


@dataclass(frozen=True, kw_only=True)
class HistogramFractionBetween:
    lookback_seconds: float
    lower_threshold: float
    upper_threshold: float
    type_: Literal["histogram_fraction_between"] = "histogram_fraction_between"


@dataclass(frozen=True, kw_only=True)
class HistogramPreserveQuantile:
    lookback_seconds: float
    percentile: float
    group_by: tuple[GraphLineGroupByKey, ...]
    type_: Literal["histogram_preserve_quantile"] = "histogram_preserve_quantile"


@dataclass(frozen=True, kw_only=True)
class HistogramPreserveFractionBelow:
    lookback_seconds: float
    threshold: float
    group_by: tuple[GraphLineGroupByKey, ...]
    type_: Literal["histogram_preserve_fraction_below"] = "histogram_preserve_fraction_below"


@dataclass(frozen=True, kw_only=True)
class HistogramPreserveFractionBetween:
    lookback_seconds: float
    lower_threshold: float
    upper_threshold: float
    group_by: tuple[GraphLineGroupByKey, ...]
    type_: Literal["histogram_preserve_fraction_between"] = "histogram_preserve_fraction_between"


type ConsolidationFunction = (
    GaugeLast
    | GaugeMax
    | GaugeAvg
    | GaugeMin
    | SumRate
    | SumLastRaw
    | SumDelta
    | HistogramQuantile
    | HistogramCountDelta
    | HistogramCountRate
    | HistogramSumRate
    | HistogramSumDelta
    | HistogramSumRaw
    | HistogramFractionBelow
    | HistogramFractionBetween
    | HistogramPreserveQuantile
    | HistogramPreserveFractionBelow
    | HistogramPreserveFractionBetween
)


def canonical_mapping_key(mapping: Mapping[str, object] | None) -> str:
    """Stable, hashable identity for an (optional) wire mapping such as an attribute
    filter or a group-by aggregator."""
    return json.dumps(mapping, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class QueryDataKey:
    metric_name: MetricName
    consolidation_function: ConsolidationFunction
    attribute_filter: Mapping[str, object]
    aggregator: Mapping[str, object] | None = None

    @override
    def __hash__(self) -> int:
        # The filter mapping is unhashable, so identity comes from its canonical serialization.
        return hash(
            (
                self.metric_name,
                self.consolidation_function,
                canonical_mapping_key(self.attribute_filter),
                canonical_mapping_key(self.aggregator),
            )
        )


@dataclass(frozen=True)
class QueryDataTimeSeries:
    time_series: TimeSeries
    id: str
    attributes: Mapping[AttributeGroup, Mapping[str, str]]


@dataclass(frozen=True, kw_only=True)
class QueryDataLimit:
    max_series_per_query: int
    num_series_per_query: int


@dataclass(frozen=True)
class QueryDataValue:
    time_series: Sequence[QueryDataTimeSeries]
    limit: QueryDataLimit


type RRDData = Mapping[RRDDataKey, TimeSeries]
type QueryData = Mapping[QueryDataKey, QueryDataValue]


@dataclass(frozen=True, kw_only=True)
class FallbackTimeRange:
    start: int
    end: int
    step: int


@dataclass(frozen=True)
class QueryDataError:
    keys: Sequence[QueryDataKey]
    exception: Exception


def _derive_num_points(
    rrd_data: RRDData,
    query_data: QueryData,
    fallback_time_range: FallbackTimeRange,
) -> tuple[int, int, int, int]:
    if rrd_data:
        sample_data = next(iter(rrd_data.values()))
        return len(sample_data), sample_data.start, sample_data.end, sample_data.step
    if query_data:
        with suppress(StopIteration):
            sample_data = next(ts for v in query_data.values() for ts in v.time_series).time_series
            return len(sample_data), sample_data.start, sample_data.end, sample_data.step
    return (
        (fallback_time_range.end - fallback_time_range.start) // fallback_time_range.step + 1,
        fallback_time_range.start,
        fallback_time_range.end,
        fallback_time_range.step,
    )


def op_func_wrapper[TOperatorReturn](
    op_func: Callable[[TimeSeries | Sequence[float | None]], TOperatorReturn],
    tsp: TimeSeries | Sequence[float | None],
) -> TOperatorReturn | None:
    if tsp.count(None) < len(tsp):  # At least one non-None value
        try:
            return op_func(tsp)
        except ZeroDivisionError:
            pass
    return None


def clean_time_series_point(tsp: TimeSeries | Sequence[float | None]) -> list[float]:
    """removes "None" entries from input list"""
    return [x for x in tsp if x is not None]


def _time_series_operator_sum(tsp: TimeSeries | Sequence[float | None]) -> float:
    return sum(clean_time_series_point(tsp))


def _time_series_operator_product(tsp: TimeSeries | Sequence[float | None]) -> float | None:
    if None in tsp:
        return None
    return functools.reduce(operator.mul, tsp, 1)


def _time_series_operator_difference(tsp: TimeSeries | Sequence[float | None]) -> float | None:
    if None in tsp:
        return None
    assert tsp[0] is not None
    assert tsp[1] is not None
    return tsp[0] - tsp[1]


def _time_series_operator_fraction(tsp: TimeSeries | Sequence[float | None]) -> float | None:
    if None in tsp or tsp[1] == 0:
        return None
    assert tsp[0] is not None
    assert tsp[1] is not None
    return tsp[0] / tsp[1]


def _time_series_operator_maximum(tsp: TimeSeries | Sequence[float | None]) -> float:
    return max(clean_time_series_point(tsp))


def _time_series_operator_minimum(tsp: TimeSeries | Sequence[float | None]) -> float:
    return min(clean_time_series_point(tsp))


def _time_series_operator_average(tsp: TimeSeries | Sequence[float | None]) -> float:
    tsp_clean = clean_time_series_point(tsp)
    return sum(tsp_clean) / len(tsp_clean)


def time_series_operators() -> dict[
    Operators,
    tuple[str, Callable[[TimeSeries | Sequence[float | None]], float | None]],
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
class AugmentedTimeSeries:
    time_series: TimeSeries
    # meta infos
    title: str | None = None
    line_type: LineType | Literal["ref"] | None = None
    color: str | None = None
    attributes: Mapping[AttributeGroup, Mapping[str, str]] = field(default_factory=dict)
    metric_name: str | None = None


@dataclass(frozen=True, kw_only=True)
class AugmentedTimeSeriesOfKeys:
    time_series: Sequence[AugmentedTimeSeries]
    limit: QueryDataLimit | None


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
        fallback_time_range: FallbackTimeRange,
    ) -> Sequence[AugmentedTimeSeriesOfKeys]: ...

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
    @override
    def plugin_name(self, instance: type[GraphMetricExpression]) -> str:
        return instance.expression_name()


graph_metric_expression_registry = GraphMetricExpressionRegistry()


def parse_graph_metric_expression(raw: object) -> GraphMetricExpression:
    match raw:  # type: ignore[exhaustive-match]
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
    @override
    def expression_name() -> Literal["constant"]:
        return "constant"

    @override
    def keys(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
    ) -> Iterator[TranslationKey | RRDDataKey | QueryDataKey]:
        yield from ()

    @override
    def compute_augmented_time_series(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        rrd_data: RRDData,
        query_data: QueryData,
        fallback_time_range: FallbackTimeRange,
    ) -> Sequence[AugmentedTimeSeriesOfKeys]:
        num_points, start, end, step = _derive_num_points(
            rrd_data,
            query_data,
            fallback_time_range,
        )
        return [
            AugmentedTimeSeriesOfKeys(
                time_series=[
                    AugmentedTimeSeries(
                        time_series=TimeSeries(
                            start=start,
                            end=end,
                            step=step,
                            values=[self.value] * num_points,
                        )
                    )
                ],
                limit=None,
            )
        ]


class GraphMetricConstantNA(GraphMetricExpression, frozen=True):
    @staticmethod
    @override
    def expression_name() -> Literal["constant_na"]:
        return "constant_na"

    @override
    def keys(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
    ) -> Iterator[TranslationKey | RRDDataKey | QueryDataKey]:
        yield from ()

    @override
    def compute_augmented_time_series(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        rrd_data: RRDData,
        query_data: QueryData,
        fallback_time_range: FallbackTimeRange,
    ) -> Sequence[AugmentedTimeSeriesOfKeys]:
        num_points, start, end, step = _derive_num_points(
            rrd_data,
            query_data,
            fallback_time_range,
        )
        return [
            AugmentedTimeSeriesOfKeys(
                time_series=[
                    AugmentedTimeSeries(
                        time_series=TimeSeries(
                            start=start,
                            end=end,
                            step=step,
                            values=[None] * num_points,
                        )
                    )
                ],
                limit=None,
            )
        ]


def _time_series_math(
    operator_id: Operators,
    operands_evaluated: list[TimeSeries],
) -> TimeSeries | None:
    operators = time_series_operators()
    if operator_id not in operators:
        raise MKGeneralException(
            _("Undefined operator '%(operator)s' in graph expression")
            % {"operator": escaping.escape_attribute(operator_id)}
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
    @override
    def expression_name() -> Literal["operator"]:
        return "operator"

    @override
    def keys(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
    ) -> Iterator[TranslationKey | RRDDataKey | QueryDataKey]:
        yield from (k for o in self.operands for k in o.keys(registered_metrics))

    @override
    def compute_augmented_time_series(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        rrd_data: RRDData,
        query_data: QueryData,
        fallback_time_range: FallbackTimeRange,
    ) -> Sequence[AugmentedTimeSeriesOfKeys]:
        if result := _time_series_math(
            self.operator_name,
            [
                ats.time_series
                for operand in self.operands
                for evaluated in operand.compute_augmented_time_series(
                    registered_metrics, rrd_data, query_data, fallback_time_range
                )
                for ats in evaluated.time_series
            ],
        ):
            return [
                AugmentedTimeSeriesOfKeys(
                    time_series=[AugmentedTimeSeries(time_series=result)],
                    limit=None,
                )
            ]
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
    @override
    def expression_name() -> Literal["rrd"]:
        return "rrd"

    @override
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

    @override
    def compute_augmented_time_series(
        self,
        registered_metrics: Mapping[str, RegisteredMetric],
        rrd_data: RRDData,
        query_data: QueryData,
        fallback_time_range: FallbackTimeRange,
    ) -> Sequence[AugmentedTimeSeriesOfKeys]:
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
            return [
                AugmentedTimeSeriesOfKeys(
                    time_series=[AugmentedTimeSeries(time_series=rrd_data[key])],
                    limit=None,
                )
            ]

        num_points, start, end, step = _derive_num_points(
            rrd_data,
            query_data,
            fallback_time_range,
        )
        return [
            AugmentedTimeSeriesOfKeys(
                time_series=[
                    AugmentedTimeSeries(
                        time_series=TimeSeries(
                            start=start,
                            end=end,
                            step=step,
                            values=[None] * num_points,
                        ),
                    )
                ],
                limit=None,
            )
        ]
