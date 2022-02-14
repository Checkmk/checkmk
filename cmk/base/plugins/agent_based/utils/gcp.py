#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from google.cloud.monitoring_v3.types import TimeSeries

from ..agent_based_api.v1 import check_levels, Service, ServiceLabel
from ..agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


@dataclass(frozen=True)
class GCPResult:
    ts: TimeSeries

    @classmethod
    def deserialize(cls, data: str) -> "GCPResult":
        b = base64.b64decode(data.encode("utf-8"))
        ts = TimeSeries.deserialize(b)
        return cls(ts=ts)


@dataclass(frozen=True)
class SectionItem:
    rows: Sequence[GCPResult]
    labels: Sequence[ServiceLabel]

    @classmethod
    def from_results(cls, rows: Sequence[GCPResult]) -> "SectionItem":
        labels = [ServiceLabel(f"gcp_{k}", v) for k, v in rows[0].ts.resource.labels.items()]
        return cls(rows=rows, labels=labels)


Section = Mapping[str, SectionItem]


def parse_gcp(string_table: StringTable, label_key: str) -> Section:
    rows = [GCPResult.deserialize(row[0]) for row in string_table[1:]]
    raw_items = json.loads(string_table[0][0])
    return {
        item["name"]: SectionItem.from_results(
            [r for r in rows if r.ts.resource.labels[label_key] == item["name"]]
        )
        for item in raw_items
    }


def discover(section: Section) -> DiscoveryResult:
    for name, item in section.items():
        yield Service(item=f"{name}", labels=list(item.labels))


@dataclass(frozen=True)
class MetricSpec:
    metric_type: str
    render_func: Callable
    has_levels: bool = False


def _get_value(results: Sequence[GCPResult], metric_type: str) -> float:
    # GCP does not always deliver all metrics. i.e. api/request_count only contains values if
    # api requests have occured. To ensure all metrics are displayed in check mk we default to
    # 0 in the absence of data.
    try:
        result = next(r for r in results if r.ts.metric.type == metric_type)
        return result.ts.points[0].value.double_value
    except StopIteration:
        return 0


def generic_check(
    metrics: Mapping[str, MetricSpec], timeseries: Sequence[GCPResult], params: Mapping[str, Any]
) -> CheckResult:
    for metric_name, metric_spec in metrics.items():
        value = _get_value(timeseries, metric_spec.metric_type)
        yield from check_levels(
            value,
            metric_name=metric_name,
            render_func=metric_spec.render_func,
            levels_upper=params.get(metric_name),
        )
