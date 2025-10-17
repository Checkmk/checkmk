#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="redundant-expr"

import json
import time
from collections.abc import Callable, Generator, Iterable, Mapping, MutableMapping, Sequence
from datetime import datetime
from enum import auto, Enum
from typing import Any, NamedTuple

from pydantic import BaseModel, Field

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v1 import Metric, Result
from cmk.agent_based.v2 import check_levels as check_levels_v2
from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    get_average,
    get_value_store,
    IgnoreResultsError,
    LevelsT,
    render,
    Service,
    ServiceLabel,
    StringTable,
)
from cmk.plugins.lib.labels import ensure_valid_labels

AZURE_AGENT_SEPARATOR = "|"


class AzureMetric(NamedTuple):
    name: str
    aggregation: str
    value: float
    unit: str


class Resource(NamedTuple):
    id: str
    name: str
    type: str
    group: str
    kind: str | None = None
    location: str | None = None
    tags: Mapping[str, str] = {}
    properties: Mapping[Any, Any] = {}
    specific_info: Mapping[Any, Any] = {}
    metrics: Mapping[str, AzureMetric] = {}
    subscription: str | None = None
    subscription_name: str | None = None
    tenant_id: str | None = None


class SustainedLevelDirection(Enum):
    """
    When using sustained threshold checking, decides if the threshold is
    an upper bound or a lower bound.
    """

    UPPER_BOUND = auto()
    LOWER_BOUND = auto()


class MetricData(NamedTuple):
    azure_metric_name: str
    metric_name: str
    metric_label: str
    render_func: Callable[[float], str]
    upper_levels_param: str = ""
    lower_levels_param: str = ""
    boundaries: tuple[float | None, float | None] | None = None

    # Apply this function to the value before using it when yielding metrics
    # This gives the opportunity to manipulate metrics before they are counted.
    map_func: Callable[[float], float] | None = None
    notice_only: bool = False
    # Optionally, average the value over time
    average_mins_param: str = ""
    # Optionally, allow for monitoring a sustained threshold
    # The Callable looks weird but allows for pulling params out of deeply nested rulespecs
    # e.g. sustained_threshold_param=lambda params: params.get("time_based", {}).get("threshold")
    sustained_threshold_param: str | Callable[[Mapping[str, Any]], str] = ""
    sustained_levels_time_param: str | Callable[[Mapping[str, Any]], str] = ""
    sustained_level_direction: SustainedLevelDirection = SustainedLevelDirection.UPPER_BOUND
    sustained_label: str | None = None


class PublicIP(BaseModel):
    name: str
    location: str
    ipAddress: str
    publicIPAllocationMethod: str
    dns_fqdn: str


class FrontendIpConfiguration(BaseModel):
    id: str
    name: str
    privateIPAllocationMethod: str
    privateIPAddress: str | None = Field(None)
    public_ip_address: PublicIP | None = Field(None)


Section = Mapping[str, Resource]
CheckFunction = Callable[[str, Mapping[str, Any], Section], CheckResult]


def parse_azure_datetime(datetime_string: str) -> datetime:
    """Return the datetime object from the parsed string.

    >>> parse_azure_datetime("2022-02-02T12:00:00.000Z")
    datetime.datetime(2022, 2, 2, 12, 0)

    >>> parse_azure_datetime("2022-02-02T12:00:00.000")
    datetime.datetime(2022, 2, 2, 12, 0)

    >>> parse_azure_datetime("2022-02-02T12:00:00.123")
    datetime.datetime(2022, 2, 2, 12, 0)

    >>> parse_azure_datetime("2022-02-02T12:00:00")
    datetime.datetime(2022, 2, 2, 12, 0)

    """
    return datetime.fromisoformat(datetime_string).replace(microsecond=0, tzinfo=None)


#   .--Parse---------------------------------------------------------------.
#   |                      ____                                            |
#   |                     |  _ \ __ _ _ __ ___  ___                        |
#   |                     | |_) / _` | '__/ __|/ _ \                       |
#   |                     |  __/ (_| | |  \__ \  __/                       |
#   |                     |_|   \__,_|_|  |___/\___|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _get_metrics_number(row: Sequence[str]) -> int:
    if str(row[0]) != "metrics following":
        return 0
    try:
        return int(row[1])
    except ValueError:
        return 0


def _get_metrics(metrics_data: Sequence[Sequence[str]]) -> Iterable[tuple[str, AzureMetric]]:
    for metric_line in metrics_data:
        metric_dict = json.loads(AZURE_AGENT_SEPARATOR.join(metric_line))

        key = f"{metric_dict['aggregation']}_{metric_dict['name'].replace(' ', '_')}"
        yield (
            key,
            AzureMetric(
                metric_dict["name"],
                metric_dict["aggregation"],
                metric_dict["value"],
                metric_dict["unit"],
            ),
        )


def _get_resource(
    resource: Mapping[str, Any], metrics: Mapping[str, AzureMetric] | None = None
) -> Resource:
    return Resource(
        resource["id"],
        resource["name"],
        resource["type"],
        resource["group"],
        resource.get("kind"),
        resource.get("location"),
        resource.get("tags", {}),
        resource.get("properties", {}),
        resource.get("specific_info", {}),
        metrics or {},
        resource.get("subscription"),
        resource.get("subscription_name"),
        resource.get("tenant_id"),
    )


def _parse_resource(resource_data: Sequence[Sequence[str]]) -> Resource | None:
    """read resource json and parse metric lines

    Metrics are stored in a dict. Key is name, prefixed by their aggregation,
    spaces become underscores:
      Disk Read Bytes|average|0.0|...
    is stored at
      resource.metrics["average_Disk_Read_Bytes"]
    """
    try:
        resource = json.loads(AZURE_AGENT_SEPARATOR.join(resource_data[0]))
    except (ValueError, IndexError):
        return None

    if len(resource_data) < 3:
        return _get_resource(resource)

    metrics_num = _get_metrics_number(resource_data[1])
    if metrics_num == 0:
        return _get_resource(resource)

    metrics = dict(_get_metrics(resource_data[2 : 2 + metrics_num]))
    return _get_resource(resource, metrics=metrics)


def parse_resources(string_table: StringTable) -> Mapping[str, Resource]:
    raw_resources: list[list[Sequence[str]]] = []

    # create list of lines per resource
    for row in string_table:
        if row == ["Resource"]:
            raw_resources.append([])
            continue
        if raw_resources:
            raw_resources[-1].append(row)

    parsed_resources = (_parse_resource(r) for r in raw_resources)

    return {r.name: r for r in parsed_resources if r}


#   .--Discovery-----------------------------------------------------------.
#   |              ____  _                                                 |
#   |             |  _ \(_)___  ___ _____   _____ _ __ _   _               |
#   |             | | | | / __|/ __/ _ \ \ / / _ \ '__| | | |              |
#   |             | |_| | \__ \ (_| (_) \ V /  __/ |  | |_| |              |
#   |             |____/|_|___/\___\___/ \_/ \___|_|   \__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+


def get_service_labels_from_resource_tags(tags: Mapping[str, str]) -> Sequence[ServiceLabel]:
    labels = ensure_valid_labels(tags)
    return [ServiceLabel(f"cmk/azure/tag/{key}", value) for key, value in labels.items()]


def create_discover_by_metrics_function(
    *desired_metrics: str,
    resource_types: Sequence[str] | None = None,
) -> Callable[[Section], DiscoveryResult]:
    """Return a discovery function, that will discover if any of the metrics are found"""

    def discovery_function(section: Section) -> DiscoveryResult:
        for item, resource in section.items():
            if (
                resource_types is None or any(rtype == resource.type for rtype in resource_types)
            ) and (set(desired_metrics) & set(resource.metrics)):
                yield Service(
                    item=item, labels=get_service_labels_from_resource_tags(resource.tags)
                )

    return discovery_function


def create_discover_by_metrics_function_single(
    *desired_metrics: str,
    resource_types: Sequence[str] | None = None,
) -> Callable[[Section], DiscoveryResult]:
    """
    Return a discovery function, that will discover if any of the metrics are found
    only if there is one resource in the section; doesn't return an item
    """

    def discovery_function(section: Section) -> DiscoveryResult:
        if len(section) != 1:
            return

        resource = list(section.values())[0]
        if (resource_types is None or any(rtype == resource.type for rtype in resource_types)) and (
            set(desired_metrics) & set(resource.metrics)
        ):
            yield Service(labels=get_service_labels_from_resource_tags(resource.tags))

    return discovery_function


#   .--Checks--------------------------------------------------------------.
#   |                    ____ _               _                            |
#   |                   / ___| |__   ___  ___| | _____                     |
#   |                  | |   | '_ \ / _ \/ __| |/ / __|                    |
#   |                  | |___| | | |  __/ (__|   <\__ \                    |
#   |                   \____|_| |_|\___|\___|_|\_\___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def iter_resource_attributes(
    resource: Resource, include_keys: tuple[str, ...] = ("location",)
) -> Generator[tuple[str, str | None]]:
    def capitalize(string: str) -> str:
        return string[0].upper() + string[1:]

    for key in include_keys:
        if (value := getattr(resource, key)) is not None:
            yield capitalize(key), value

    for key, value in sorted(resource.tags.items()):
        if not key.startswith("hidden-"):
            yield capitalize(key), value


def check_resource_metrics(
    resource: Resource,
    params: Mapping[str, Any],
    metrics_data: Sequence[MetricData],
    suppress_error: bool = False,
    check_levels: Callable[..., Iterable[Result | Metric]] = check_levels_v1,
) -> CheckResult:
    metrics = [resource.metrics.get(m.azure_metric_name) for m in metrics_data]
    if not any(metrics) and not suppress_error:
        raise IgnoreResultsError("Data not present at the moment")

    now = time.time()

    for metric, metric_data in zip(metrics, metrics_data):
        if not metric:
            continue

        if isinstance(metric_data.sustained_threshold_param, str):
            threshold = params.get(metric_data.sustained_threshold_param)
        else:
            threshold = metric_data.sustained_threshold_param(params)

        if isinstance(metric_data.sustained_levels_time_param, str):
            threshold_levels = params.get(metric_data.sustained_levels_time_param)
        else:
            threshold_levels = metric_data.sustained_levels_time_param(params)

        if threshold and threshold_levels:
            yield from _threshold_hit_for_time(
                current_value=(
                    metric_data.map_func(metric.value) if metric_data.map_func else metric.value
                ),
                threshold=threshold,
                limits=threshold_levels,
                now=now,
                value_store=get_value_store(),
                value_store_key=f"{metric_data.metric_name}_sustained_threshold",
                direction=metric_data.sustained_level_direction,
                label=metric_data.sustained_label,
            )

        if (
            metric_data.average_mins_param is not None
            and (average_mins := params.get(metric_data.average_mins_param)) is not None
        ):
            # Even if we alert on the average, we still emit the instantaneous value as a metric.
            yield Metric(metric_data.metric_name, metric.value)
            metric_name = f"{metric_data.metric_name}_average"
            metric_value = get_average(
                get_value_store(),
                metric_name,  # value_store key, we just use the metric name
                now,
                metric.value,
                average_mins,
            )
        else:
            metric_name = metric_data.metric_name
            metric_value = metric.value

        yield from check_levels(
            metric_data.map_func(metric_value) if metric_data.map_func else metric_value,
            levels_upper=params.get(metric_data.upper_levels_param),
            levels_lower=params.get(metric_data.lower_levels_param),
            metric_name=metric_name,
            label=metric_data.metric_label,
            render_func=metric_data.render_func,
            boundaries=metric_data.boundaries,
            notice_only=metric_data.notice_only,
        )


def create_check_metrics_function(
    metrics_data: Sequence[MetricData],
    suppress_error: bool = False,
    check_levels: Callable[..., Iterable[Result | Metric]] = check_levels_v1,
) -> Callable[[str, Mapping[str, Any], Section], CheckResult]:
    def check_metric(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
        resource = section.get(item)
        if not resource:
            if suppress_error:
                return
            raise IgnoreResultsError("Data not present at the moment")

        yield from check_resource_metrics(
            resource, params, metrics_data, suppress_error, check_levels
        )

    return check_metric


def create_check_metrics_function_single(
    metrics_data: Sequence[MetricData],
    suppress_error: bool = False,
    check_levels: Callable[..., Iterable[Result | Metric]] = check_levels_v1,
) -> Callable[[Mapping[str, Any], Section], CheckResult]:
    def check_metric(params: Mapping[str, Any], section: Section) -> CheckResult:
        if len(section) != 1:
            if suppress_error:
                return
            raise IgnoreResultsError("Only one resource expected")

        resource = list(section.values())[0]
        yield from check_resource_metrics(
            resource, params, metrics_data, suppress_error, check_levels
        )

    return check_metric


def check_memory() -> CheckFunction:
    return create_check_metrics_function(
        [
            MetricData(
                "average_memory_percent",
                "mem_used_percent",
                "Memory utilization",
                render.percent,
                upper_levels_param="levels",
            )
        ]
    )


def check_cpu() -> CheckFunction:
    return create_check_metrics_function(
        [
            MetricData(
                "average_cpu_percent",
                "util",
                "CPU utilization",
                render.percent,
                upper_levels_param="levels",
            )
        ]
    )


def check_connections() -> CheckFunction:
    return create_check_metrics_function(
        [
            MetricData(
                "average_active_connections",
                "active_connections",
                "Active connections",
                lambda x: str(int(x)),
                lower_levels_param="active_connections_lower",
                upper_levels_param="active_connections",
            ),
            MetricData(
                "total_connections_failed",
                "failed_connections",
                "Failed connections",
                lambda x: str(int(x)),
                upper_levels_param="failed_connections",
            ),
            MetricData(
                # MySQL flexible server equivalent to "total_connections_failed"
                "total_aborted_connections",
                "failed_connections",
                "Failed connections",
                lambda x: str(int(x)),
                upper_levels_param="failed_connections",
            ),
        ]
    )


def check_network() -> CheckFunction:
    return create_check_metrics_function(
        [
            MetricData(
                "total_network_bytes_ingress",
                "ingress",
                "Network in",
                render.bytes,
                upper_levels_param="ingress_levels",
            ),
            MetricData(
                "total_network_bytes_egress",
                "egress",
                "Network out",
                render.bytes,
                upper_levels_param="egress_levels",
            ),
        ]
    )


def check_storage() -> CheckFunction:
    return create_check_metrics_function(
        [
            MetricData(
                "average_io_consumption_percent",
                "io_consumption_percent",
                "IO",
                render.percent,
                upper_levels_param="io_consumption",
            ),
            MetricData(
                "average_storage_percent",
                "storage_percent",
                "Storage",
                render.percent,
                upper_levels_param="storage",
            ),
            MetricData(
                "average_serverlog_storage_percent",
                "serverlog_storage_percent",
                "Server log storage",
                render.percent,
                upper_levels_param="serverlog_storage",
            ),
        ]
    )


def _threshold_hit_for_time[NumberT: (int, float)](
    current_value: float,
    threshold: float,
    # We assume v2-style limits
    limits: LevelsT[NumberT],
    now: float,
    value_store: MutableMapping[str, Any],
    value_store_key: str,
    direction: SustainedLevelDirection = SustainedLevelDirection.UPPER_BOUND,
    label: str | None = None,
) -> CheckResult:
    """
    Alert if the threshold has been hit or exceeded for longer than 'limits'
    amount of time.

    To accomplish this, when the threshold is hit, the timestamp is stored in the
    value store. Later, if the threshold is NOT met, the timestamp is removed from
    the value store. Otherwise if the threshold is still hit, the time since the
    original hit is compared to the current time, and if more seconds have
    elapsed than 'limits' allows, an alert is raised.

    The 'value_store_key' is required so that this can be used multiple times
    in one check plugin (to check different kinds of values).

    If 'direction' is LOWER_BOUND, then the alerting happens when the
    value dips and stays _below_ the threshold.
    """
    if direction == SustainedLevelDirection.LOWER_BOUND:
        drop_from_value_store = current_value > threshold
        if label is None:
            label = "Below the threshold for"
    else:
        drop_from_value_store = current_value < threshold
        if label is None:
            label = "Above the threshold for"

    if drop_from_value_store:
        # If we are under the threshold, clear out any previous record of
        # being over it, because now it doesn't matter anymore, we're not
        # going to alert.
        value_store[value_store_key] = None
    else:
        # Otherwise we're at or over the threshold.
        threshold_hit_time = value_store.get(value_store_key)
        if threshold_hit_time is None:
            # This is the first time we're over the threshold in this "series"
            # Don't alert here, just store the value in case we need to alert next time
            value_store[value_store_key] = now
        else:
            # We already had a value stored from before, compare it to see
            # if it's time to alert.
            yield from check_levels_v2(
                now - threshold_hit_time,
                levels_upper=limits,
                render_func=render.timespan,
                label=label,
                notice_only=True,
            )
