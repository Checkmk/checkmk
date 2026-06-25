#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import calendar
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.graylog.lib import deserialize_and_merge_json

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


@dataclass(frozen=True)
class Section:
    input: Mapping[str, int] | None
    output: Mapping[str, int] | None
    decoded: Mapping[str, int] | None
    to: str | None


class GraylogClusterTrafficParams(TypedDict):
    input: LevelsT[int]
    output: LevelsT[int]
    decoded: LevelsT[int]


def parse_graylog_cluster_traffic(string_table: StringTable) -> Section:
    match deserialize_and_merge_json(string_table):
        case {
            "input": dict() | None as input_,
            "output": dict() | None as output,
            "decoded": dict() | None as decoded,
            "to": str() | None as to,
        }:
            return Section(input=input_, output=output, decoded=decoded, to=to)
        case _:
            return Section(input=None, output=None, decoded=None, to=None)


def discover_graylog_cluster_traffic(section: Section) -> DiscoveryResult:
    if section.input or section.output or section.decoded or section.to:
        yield Service()


def check_graylog_cluster_traffic(
    params: GraylogClusterTrafficParams, section: Section
) -> CheckResult:
    for traffic, metric_name, infotext, levels_upper in [
        (section.input, "graylog_input", "Input", params["input"]),
        (section.output, "graylog_output", "Output", params["output"]),
        (section.decoded, "graylog_decoded", "Decoded", params["decoded"]),
    ]:
        if not traffic:
            continue

        latest_entry = sorted(traffic, reverse=True)[0]
        yield from check_levels(
            value=traffic[latest_entry],
            metric_name=metric_name,
            levels_upper=levels_upper,
            render_func=render.bytes,
            label=infotext,
        )

    if section.to is not None:
        local_timestamp = calendar.timegm(time.strptime(section.to, "%Y-%m-%dT%H:%M:%S.%fZ"))
        yield Result(
            state=State.OK,
            summary=f"Last updated: {render.datetime(local_timestamp)}",
        )


agent_section_graylog_cluster_traffic = AgentSection(
    name="graylog_cluster_traffic",
    parse_function=parse_graylog_cluster_traffic,
)


check_plugin_graylog_cluster_traffic = CheckPlugin(
    name="graylog_cluster_traffic",
    service_name="Graylog Cluster Traffic",
    discovery_function=discover_graylog_cluster_traffic,
    check_function=check_graylog_cluster_traffic,
    check_ruleset_name="graylog_cluster_traffic",
    check_default_parameters={
        "input": ("no_levels", None),
        "output": ("no_levels", None),
        "decoded": ("no_levels", None),
    },
)
