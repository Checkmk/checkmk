#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Generator, Iterable, Mapping, Sequence
from typing import Any, NamedTuple

from pydantic import BaseModel, Field

from cmk.agent_based.v2 import (
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

        prefix = (
            ""
            if (dimension_filter := metric_dict.get("dimension_filter")) is None
            else "".join(dimension_filter)
        )
        key = f"{prefix}{metric_dict['aggregation']}_{metric_dict['name'].replace(' ', '_')}"
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
