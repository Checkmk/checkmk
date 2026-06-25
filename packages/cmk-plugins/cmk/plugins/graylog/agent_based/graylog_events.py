#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
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
    Service,
    StringTable,
)

# <<<graylog_events>>>
# {"events": {"num_of_events": 3, "has_since_argument": false, "events_since": null, "num_of_events_in_range": 0}}

# <<<graylog_events>>>
# {"events": {"num_of_events": 5, "has_since_argument": true, "events_since": 1800, "num_of_events_in_range": 2}}


@dataclass
class EventsInfo:
    num_of_events: int
    has_since_argument: bool
    events_since: int | None
    num_of_events_in_range: int


class EventsParams(TypedDict):
    events_upper: LevelsT[int]
    events_lower: LevelsT[int]
    events_in_range_upper: LevelsT[int]
    events_in_range_lower: LevelsT[int]


def parse_graylog_events(string_table: StringTable) -> EventsInfo | None:
    try:
        raw = json.loads(string_table[0][0])
    except IndexError:
        return None

    match raw.get("events"):
        case {
            "num_of_events": int(num_of_events),
            "has_since_argument": bool(has_since_argument),
            "events_since": int() | None as events_since,
            "num_of_events_in_range": int(num_of_events_in_range),
        }:
            return EventsInfo(
                num_of_events=num_of_events,
                has_since_argument=has_since_argument,
                events_since=events_since,
                num_of_events_in_range=num_of_events_in_range,
            )
        case _:
            return None


agent_section_graylog_events = AgentSection(
    name="graylog_events",
    parse_function=parse_graylog_events,
)


def discover_graylog_events(section: EventsInfo) -> DiscoveryResult:
    yield Service(item=None)


def check_graylog_events(params: EventsParams, section: EventsInfo) -> CheckResult:
    yield from check_levels(
        value=section.num_of_events,
        levels_upper=params["events_upper"],
        levels_lower=params["events_lower"],
        render_func=str,
        label="Total number of events in the last 24 hours",
    )

    if section.has_since_argument and section.events_since:
        yield from check_levels(
            value=section.num_of_events_in_range,
            levels_upper=params["events_in_range_upper"],
            levels_lower=params["events_in_range_lower"],
            render_func=str,
            label=f"Total number of events in the last {render.timespan(section.events_since)}",
        )


check_plugin_graylog_events = CheckPlugin(
    name="graylog_events",
    check_function=check_graylog_events,
    discovery_function=discover_graylog_events,
    service_name="Graylog Cluster Events",
    check_default_parameters={
        "events_upper": ("no_levels", None),
        "events_lower": ("no_levels", None),
        "events_in_range_upper": ("no_levels", None),
        "events_in_range_lower": ("no_levels", None),
    },
    check_ruleset_name="graylog_events",
)
