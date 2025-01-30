#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable, Generator, Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any, NamedTuple

from pydantic import BaseModel, Field

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    render,
    Service,
    ServiceLabel,
    StringTable,
)
from cmk.plugins.lib.labels import custom_tags_to_valid_labels

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


class MetricData(NamedTuple):
    azure_metric_name: str
    metric_name: str
    metric_label: str
    render_func: Callable[[float], str]
    upper_levels_param: str = ""
    lower_levels_param: str = ""
    boundaries: tuple[float | None, float | None] | None = None


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
    labels = custom_tags_to_valid_labels(tags)
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
) -> Generator[tuple[str, str | None], None, None]:
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
) -> CheckResult:
    metrics = [resource.metrics.get(m.azure_metric_name) for m in metrics_data]
    if not any(metrics) and not suppress_error:
        raise IgnoreResultsError("Data not present at the moment")

    for metric, metric_data in zip(metrics, metrics_data):
        if not metric:
            continue

        yield from check_levels_v1(
            metric.value,
            levels_upper=params.get(metric_data.upper_levels_param),
            levels_lower=params.get(metric_data.lower_levels_param),
            metric_name=metric_data.metric_name,
            label=metric_data.metric_label,
            render_func=metric_data.render_func,
            boundaries=metric_data.boundaries,
        )


def create_check_metrics_function(
    metrics_data: Sequence[MetricData], suppress_error: bool = False
) -> Callable[[str, Mapping[str, Any], Section], CheckResult]:
    def check_metric(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
        resource = section.get(item)
        if not resource:
            if suppress_error:
                return
            raise IgnoreResultsError("Data not present at the moment")

        yield from check_resource_metrics(resource, params, metrics_data, suppress_error)

    return check_metric


def create_check_metrics_function_single(
    metrics_data: Sequence[MetricData], suppress_error: bool = False
) -> Callable[[Mapping[str, Any], Section], CheckResult]:
    def check_metric(params: Mapping[str, Any], section: Section) -> CheckResult:
        if len(section) != 1:
            if suppress_error:
                return
            raise IgnoreResultsError("Only one resource expected")

        resource = list(section.values())[0]
        yield from check_resource_metrics(resource, params, metrics_data, suppress_error)

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
