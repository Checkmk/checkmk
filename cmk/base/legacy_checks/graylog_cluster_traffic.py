#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import calendar
import time
from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.plugins.lib.graylog import deserialize_and_merge_json, GraylogSection

check_info = {}

# <<<graylog_cluster_traffic>>>
# {"to": "2019-09-20T12:00:00.000Z", "output": {"2019-09-17T03:00:00.000Z":
# 6511247, "2019-09-18T14:00:00.000Z": 176026381, "2019-09-08T08:00:00.000Z":
# 5879007, "2019-09-15T17:00:00.000Z": 6125353, "2019-09-19T00:00:00.000Z":
# 171947147, "2019-09-04T21:00:00.000Z": 3898949, "2019-09-09T04:00:00.000Z":
# 7305970, "2019-09-07T02:00:00.000Z": 5892132, "2019-09-15T13:00:00.000Z":
# 5918729, "2019-09-17T01:00:00.000Z": 6204003, "2019-09-03T20:00:00.000Z":
# 3491202, "2019-09-17T06:00:00.000Z": 12998748, "2019-09-12T22:00:00.000Z":
# 10281903, "2019-09-06T12:00:00.000Z": 11985705, "2019-09-05T16:00:00.000Z":
# 6598880, "2019-09-13T21:00:00.000Z": 6335781, "2019-09-18T08:00:00.000Z":
# 177931813, "2019-09-15T22:00:00.000Z": 6131828, "2019-09-18T10:00:00.000Z":
# 178435781, "2019-09-15T02:00:00.000Z": 5913174, "2019-09-18T12:00:00.000Z":
# 180571316, "2019-09-17T09:00:00.000Z": 17555409, "2019-09-16T09:00:00.000Z":
# 15022425, "2019-09-10T21:00:00.000Z": 7688443}}


def discover_graylog_cluster_traffic(section: GraylogSection) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_graylog_cluster_traffic(_no_item, params, parsed):
    if parsed is None:
        return

    for key, infotext in [
        ("input", "Input"),
        ("output", "Output"),
        ("decoded", "Decoded"),
    ]:
        traffic_value = parsed.get(key)
        if traffic_value is not None:
            try:
                latest_entry = sorted(traffic_value, reverse=True)[0]
            except IndexError:
                continue

            yield check_levels(
                traffic_value[latest_entry],
                "graylog_%s" % key,
                params.get(key),
                infoname=infotext,
                human_readable_func=render.bytes,
            )

    last_updated = parsed.get("to")
    if last_updated is not None:
        local_timestamp = calendar.timegm(time.strptime(last_updated, "%Y-%m-%dT%H:%M:%S.%fZ"))

        yield 0, "Last updated: %s" % render.datetime(local_timestamp)


check_info["graylog_cluster_traffic"] = LegacyCheckDefinition(
    name="graylog_cluster_traffic",
    parse_function=deserialize_and_merge_json,
    service_name="Graylog Cluster Traffic",
    discovery_function=discover_graylog_cluster_traffic,
    check_function=check_graylog_cluster_traffic,
    check_ruleset_name="graylog_cluster_traffic",
)
