#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Callable, Iterable, Mapping
from typing import TypeVar

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyResult
from cmk.agent_based.v2 import (
    get_rate,
    get_value_store,
    IgnoreResultsError,
    render,
    Service,
)
from cmk.plugins.lib.azure import (
    get_service_labels_from_resource_tags,
    Resource,
)

_AZURE_METRIC_FMT = {
    "count": lambda n: "%d" % n,
    "percent": render.percent,
    "bytes": render.bytes,
    "bytes_per_second": render.iobandwidth,
    "seconds": lambda s: "%.2f s" % s,
    "milli_seconds": lambda ms: "%d ms" % (ms * 1000),
    "milliseconds": lambda ms: "%d ms" % (ms * 1000),
}


_Data = TypeVar("_Data")


def get_data_or_go_stale(item: str, section: Mapping[str, _Data]) -> _Data:
    if resource := section.get(item):
        return resource
    raise IgnoreResultsError("Data not present at the moment")


def check_azure_metric(
    resource: Resource,
    metric_key: str,
    cmk_key: str,
    display_name: str,
    levels: tuple[float, float] | None = None,
    levels_lower: tuple[float, float] | None = None,
    use_rate: bool = False,
) -> None | LegacyResult:
    metric = resource.metrics.get(metric_key)
    if metric is None:
        return None

    if use_rate:
        countername = f"{resource.id}.{metric_key}"
        value = get_rate(
            get_value_store(), countername, time.time(), metric.value, raise_overflow=True
        )
        unit = "%s_rate" % metric.unit
    else:
        value = metric.value
        unit = metric.unit

    if value is None:
        return 3, "Metric %s is 'None'" % display_name, []

    # convert to SI-unit
    if unit in ("milli_seconds", "milliseconds"):
        value /= 1000.0
    elif unit == "seconds_rate":
        # we got seconds, but we computed the rate -> seconds per second:
        # how long happend something / time period = percent of the time
        # e.g. CPU time: how much percent of of the time was the CPU busy.
        value *= 100.0
        unit = "percent"

    return check_levels(
        value,
        cmk_key,
        (levels or (None, None)) + (levels_lower or (None, None)),
        infoname=display_name,
        human_readable_func=_AZURE_METRIC_FMT.get(unit, lambda x: f"{x}"),
        boundaries=(0, None),
    )


def discover_azure_by_metrics(
    *desired_metrics: str,
) -> Callable[[Mapping[str, Resource]], Iterable[Service]]:
    """Return a discovery function, that will discover if any of the metrics are found"""

    def discovery_function(parsed):
        for name, resource in parsed.items():
            metr = resource.metrics
            if set(desired_metrics) & set(metr):
                yield Service(
                    item=name, labels=get_service_labels_from_resource_tags(resource.tags)
                )

    return discovery_function
