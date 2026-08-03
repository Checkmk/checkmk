#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from cmk.agent_based.v2 import HostLabelGenerator

from ._metrics_models import MetricsRecord
from ._naming import validate_name

# The host label function's signature depends on whether a ruleset is used:
# (section) without one, (params, section) with one.
type _HostLabelFunction = Callable[..., HostLabelGenerator]


# NOTE: The dataclasses below duplicate quite a few things from
# cmk.metric_backend.query.models.attribute_filter. Is there a
# reason for not simply using the metric backend data types?


@dataclass(kw_only=True, frozen=True)
class ScopeFilter:
    key: str
    value: str


@dataclass(kw_only=True, frozen=True)
class ResourceFilter:
    key: str
    value: str


@dataclass(kw_only=True, frozen=True)
class DatapointFilter:
    key: str
    value: str


AttributeFilter = ScopeFilter | DatapointFilter | ResourceFilter


@dataclass(kw_only=True, frozen=True)
class GaugeAggregation:
    """
    Gauge data point types will always return the latest value of the last minute.
    """

    lookback_minutes: int = 1


@dataclass(kw_only=True, frozen=True)
class SumAggregation:
    """
    Sum data point types will always return the delta value between the first and the last value
    in the aggregation timespan, even when the data point is cumulative.
    Therefor the aggregation minutes should be set to a multiple (5x) of datapoint emission period.
    E.g. when a datapoint is emitted every minute, aggregation minutes should be at least 5 minutes.
    The timespan is the time from the execution of the check minus the aggregation_minutes.
    """

    aggregation_minutes: int = 1


@dataclass(kw_only=True, frozen=True)
class HistogramAggregation:
    """
    Histogram data point types will always return the delta for count and rate between the first and
    last data point in the aggregation timespan, even when the data point is cumulative.
    Therefor the aggregation minutes should be set to a multiple (5x) of datapoint emission period.
    E.g. when a datapoint is emitted every minute, aggregation minutes should be at least 5 minutes.
    The timespan is the time from the execution of the check minus the aggregation_minutes.

    A list of quantiles can be provided to calculate the distribution of values in the buckets.
    The values must be provided between 0 and 1, and will be returned in the same order as provided.
    """

    aggregation_minutes: int = 1
    quantiles: Sequence[float] = field(default_factory=list)


@dataclass(kw_only=True, frozen=True)
class InstantAggregation:
    """
    Returns the value for the smallest possible time range for all data points.
    Currently, that is 1 minute.
    """

    lookback_minutes: int = 1


Aggregation = GaugeAggregation | SumAggregation | HistogramAggregation | InstantAggregation


@dataclass(kw_only=True, frozen=True)
class MetricSelector:
    """
    Configuration object for selecting metric sections.

    [metric_name AND [attribute_filter AND attribute_filter]]

    Args:
        name:               A arbitrary string that identifies the selector and will be returned with the selected data point
        metric_name:        A metric name to be filtered for
        attribute_filters:  Only data points that match all provided filters will match
        aggregation:        Aggregation object, that determines how values are aggregated over a
                            defined time range.
                            For "instant" values choose 1 minute as the time range.
                            Not setting the aggregation will return the "instant" value, independent of datatype.
    """

    name: str = ""
    metric_name: str | None
    attribute_filters: Sequence[AttributeFilter] = ()
    aggregation: Aggregation = InstantAggregation()


@dataclass(kw_only=True, frozen=True)
class MetricsSection[Section]:
    """
    An agent section that pre-filters raw agent data
    from the metric backend as a data source.

    Instances will only be picked up by Checkmk if their names start
    with ``metrics_section_``.

    Args:
        name:                 The unique name of the section to be registered.
        selectors:            A list of selectors to apply to the metric backend
                              to filter for data.
        parse_function:       The function turning the deserialized
                              :class:`MetricsRecord` instances into the
                              section's data format.
        host_label_function:  The function responsible for extracting host labels from
                              the parsed data. For unparameterized host label functions,
                              it must accept exactly one argument by the name 'section'.
                              When used in conjunction with a ruleset, it must accept two
                              arguments: 'params' and 'section'.
                              'params' will be a single mapping: the merged result of the
                              effective rules of the host label ruleset.
                              'section' will be the parsed data as returned by the parse
                              function.
                              It is expected to yield objects of type :class:`HostLabel`.
        host_label_default_parameters: Default parameters for the host label function.
                              Must match the ValueSpec of the corresponding WATO ruleset,
                              if it exists.
        host_label_ruleset_name: The name of the host label ruleset.
        parsed_section_name:  The name of the parsed section (defaults to the section name).
        supersedes:           A list of section names this section supersedes.

    Example:
        Get all data points for the cpu.aggregated metric. If the data points returned are
        of metric type Gauge, only the latest value will be returned
        >>> metrics_section_example = MetricsSection(
        ...     name="example_check_plugin",
        ...     selectors=[MetricSelector(
        ...         name="filter_gauge",
        ...         metric_name="cpu.frequency",
        ...     )],
        ...     parse_function=lambda x: x
        ... )

        Get all aggregated data points for the http.server.requests.duration metric
        produced by a (made-up) http-collector exporter for the last minute
        >>> metrics_section_example = MetricsSection(
        ...     name="example_check_plugin",
        ...     selectors=[MetricSelector(
        ...         name="filter_1",
        ...         metric_name="http.server.requests.duration",
        ...         attribute_filters=[
        ...             ScopeFilter(
        ...                 key="exporter",
        ...                 value="http-collector.github.com"
        ...             )
        ...         ],
        ...     )],
        ...     parse_function=lambda x: x
        ... )

        Get all aggregated data points for the http.server.requests.duration metric
        (which is a histogram metric), aggregated over the last 60 minutes with
        precalculated percentiles for the 50th (mean) and 99th percentile
        >>> metrics_section_example = MetricsSection(
        ...     name="example_check_plugin",
        ...     selectors=[MetricSelector(
        ...         name="filter_60",
        ...         metric_name="http.server.requests.duration",
        ...         aggregation=HistogramAggregation(
        ...             aggregation_minutes=60,
        ...             quantiles=[0.50, 0.99]
        ...         )
        ...     )],
        ...     parse_function=lambda x: x
        ... )

        Get all aggregated data points for the http.server.requests.duration metric
        (which is a histogram metric), aggregated over the last 15 minutes with
        precalculated percentiles for the 50th (mean) and 99th percentile
        as well as all aggregated data points over the last 60 minutes with
        precalculated percentiles for the 75th and 99th percentile
        >>> metrics_section_example = MetricsSection(
        ...     name="example_check_plugin",
        ...     selectors=[MetricSelector(
        ...         name="filter_15",
        ...         metric_name="http.server.requests.duration",
        ...         aggregation=HistogramAggregation(
        ...             aggregation_minutes=15,
        ...             quantiles=[0.50, 0.99]
        ...         )
        ...     ),
        ...     MetricSelector(
        ...         name="filter_60",
        ...         metric_name="http.server.requests.duration",
        ...         aggregation=HistogramAggregation(
        ...             aggregation_minutes=60,
        ...             quantiles=[0.75, 0.99]
        ...         )
        ...     )],
        ...     parse_function=lambda x: x
        ... )
    """

    name: str
    selectors: Sequence[MetricSelector]
    parse_function: Callable[[Sequence[MetricsRecord]], Section | None]
    host_label_function: _HostLabelFunction | None = None
    host_label_default_parameters: Mapping[str, object] | None = None
    host_label_ruleset_name: str | None = None
    parsed_section_name: str | None = None
    supersedes: Sequence[str] | None = None

    def __post_init__(self) -> None:
        _ = validate_name(self.name)
        if self.parsed_section_name is not None:
            _ = validate_name(self.parsed_section_name)
