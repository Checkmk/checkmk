#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import json
import time
from typing import Any, List, NamedTuple

from cmk.base.check_api import (
    check_levels,
    get_bytes_human_readable,
    get_percent_human_readable,
    get_rate,
    MKCounterWrapped,
)

_AZURE_METRIC_FMT = {
    "count": lambda n: "%d" % n,
    "percent": get_percent_human_readable,
    "bytes": get_bytes_human_readable,
    "bytes_per_second": lambda b: "%s/s" % get_bytes_human_readable(b),
    "seconds": lambda s: "%.2f s" % s,
    "milli_seconds": lambda ms: "%d ms" % (ms * 1000),
}


def get_data_or_go_stale(check_function):
    """Variant of get_parsed_item_data that raises MKCounterWrapped
    if data is not found.
    """

    @functools.wraps(check_function)
    def wrapped_check_function(item, params, parsed):
        if not isinstance(parsed, dict):
            return 3, "Wrong usage of decorator: parsed is not a dict"
        if item not in parsed or not parsed[item]:
            raise MKCounterWrapped("Data not present at the moment")
        return check_function(item, params, parsed[item])

    return wrapped_check_function


def azure_iter_informative_attrs(resource, include_keys=("location",)):
    def cap(string):  # not quite what str.title() does
        return string[0].upper() + string[1:]

    for key in include_keys:
        if key in resource:
            yield cap(key), resource[key]

    for key, value in sorted(resource.get("tags", {}).items()):
        if not key.startswith("hidden-"):
            yield cap(key), value


def check_azure_metric(  # pylint: disable=too-many-locals
    resource, metric_key, cmk_key, display_name, levels=None, levels_lower=None, use_rate=False
):
    metric = resource.get("metrics", {}).get(metric_key)
    if metric is None:
        return None

    if use_rate:
        countername = "%s.%s" % (resource["id"], metric_key)
        value = get_rate(countername, time.time(), metric.value)
        unit = "%s_rate" % metric.unit
    else:
        value = metric.value
        unit = metric.unit

    if value is None:
        return 3, "Metric %s is 'None'" % display_name, []

    # convert to SI-unit
    if unit == "milli_seconds":
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
        human_readable_func=_AZURE_METRIC_FMT.get(unit, str),  # type: ignore[arg-type]
        boundaries=(0, None),
    )


#   .--Parse---------------------------------------------------------------.
#   |                      ____                                            |
#   |                     |  _ \ __ _ _ __ ___  ___                        |
#   |                     | |_) / _` | '__/ __|/ _ \                       |
#   |                     |  __/ (_| | |  \__ \  __/                       |
#   |                     |_|   \__,_|_|  |___/\___|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

AZURE_AGENT_SEPARATOR = "|"


class Metric(NamedTuple):
    name: Any
    aggregation: Any
    value: float
    unit: str
    timestamp: Any
    timegrain: Any
    filters: Any


def _read(row, types, defaults=None):
    if defaults is None:
        defaults = [None for __ in types]
    if len(defaults) != len(types):
        raise ValueError("expected %d default values" % len(types))

    for i, (tfunc, default) in enumerate(zip(types, defaults)):
        try:
            raw = row[i]
            yield tfunc(raw)
        except (IndexError, ValueError):
            yield default


def _parse_resource(info):
    """read resource json and parse metric lines

    Metrics are stored in a dict. Key is name, prefixed by their aggregation,
    spaces become underspcores:
      Disk Read Bytes|average|0.0|...
    is stored at
      resource["metrics"]["average_Disk_Read_Bytes"]
    """
    try:
        resource = json.loads(AZURE_AGENT_SEPARATOR.join(info[0]))
    except (ValueError, IndexError):
        return None

    if len(info) < 3:
        return resource

    key, count = _read(info[1], (str, int), ("", 0))
    if key != "metrics following":
        return resource

    for mline in info[2 : 2 + count]:
        metric_dict = json.loads(AZURE_AGENT_SEPARATOR.join(mline))
        value = metric_dict["value"]
        if metric_dict["unit"] in ("count", "bytes") and value is not None:
            value = int(value)

        key = "%s_%s" % (metric_dict["aggregation"], metric_dict["name"].replace(" ", "_"))
        metr = Metric(
            metric_dict["name"],
            metric_dict["aggregation"],
            value,
            metric_dict["unit"],
            metric_dict["timestamp"],
            metric_dict["interval_id"],
            metric_dict["filter"],
        )
        resource.setdefault("metrics", {})[key] = metr

    return resource


def parse_azure(info):
    raw_resources: List[Any] = []

    # create list of lines per resource
    for row in info:
        if row == ["Resource"]:
            raw_resources.append([])
            continue
        if raw_resources:
            raw_resources[-1].append(row)

    parsed_resources = (_parse_resource(r) for r in raw_resources)

    return {r["name"]: r for r in parsed_resources if r}


# .

#   .--Discovery-----------------------------------------------------------.
#   |              ____  _                                                 |
#   |             |  _ \(_)___  ___ _____   _____ _ __ _   _               |
#   |             | | | | / __|/ __/ _ \ \ / / _ \ '__| | | |              |
#   |             | |_| | \__ \ (_| (_) \ V /  __/ |  | |_| |              |
#   |             |____/|_|___/\___\___/ \_/ \___|_|   \__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+


def discover_azure_by_metrics(*desired_metrics):
    """Return a discovery function, that will discover if any of the metrics are found"""

    def discovery_function(parsed):
        for name, resource in parsed.items():
            metr = resource.get("metrics", {})
            if set(desired_metrics) & set(metr):
                yield name, {}

    return discovery_function


# .
