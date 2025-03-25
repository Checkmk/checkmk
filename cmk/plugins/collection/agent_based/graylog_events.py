#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
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


EventsInfoSection = EventsInfo | None


def parse_graylog_events(string_table: StringTable) -> EventsInfoSection:
    try:
        events_data = json.loads(string_table[0][0]).get("events")
    except IndexError:
        return None

    return EventsInfo(
        num_of_events=int(events_data.get("num_of_events")),
        has_since_argument=events_data.get("has_since_argument"),
        events_since=(
            int(events_data.get("events_since")) if events_data.get("events_since") else None
        ),
        num_of_events_in_range=int(events_data.get("num_of_events_in_range")),
    )


agent_section_graylog_events = AgentSection(
    name="graylog_events",
    parse_function=parse_graylog_events,
)


def discover_graylog_events(section: EventsInfoSection) -> DiscoveryResult:
    if section:
        yield Service(item=None)


def check_graylog_events(params: Mapping[str, Any], section: EventsInfoSection) -> CheckResult:
    if not section:
        return

    yield from check_levels_v1(
        value=section.num_of_events,
        levels_upper=params.get("events_upper", (None, None)),
        levels_lower=params.get("events_lower", (None, None)),
        render_func=str,
        label="Total number of events in the last 24 hours",
    )

    if section.has_since_argument and section.events_since:
        yield from check_levels_v1(
            value=section.num_of_events_in_range,
            levels_upper=params.get("events_in_range_upper", (None, None)),
            levels_lower=params.get("events_in_range_lower", (None, None)),
            render_func=str,
            label=f"Total number of events in the last {render.timespan(section.events_since)}",
        )


check_plugin_graylog_events = CheckPlugin(
    name="graylog_events",
    check_function=check_graylog_events,
    discovery_function=discover_graylog_events,
    service_name="Graylog Cluster Events",
    check_default_parameters={},
    check_ruleset_name="graylog_events",
)
