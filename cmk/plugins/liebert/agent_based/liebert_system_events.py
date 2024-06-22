#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.liebert.agent_based.lib import DETECT_LIEBERT, parse_liebert_without_unit

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.100.4618 Ambient Air Temperature Sensor Issue
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.100.4618 Inactive Event
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.100.4645 Supply Fluid Over Temp
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.100.4645 Inactive Event
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.100.4648 Supply Fluid Under Temp
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.100.4648 Inactive Event
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.100.4651 Supply Fluid Temp Sensor Issue
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.100.4651 Active Warning
# and much more...


class Section(TypedDict, total=True):
    events: Mapping[str, str]


def parse_liebert_system_events(string_table: StringTable) -> Section:
    return {"events": parse_liebert_without_unit([string_table], str)}


def discover_liebert_system_events(section: Section) -> DiscoveryResult:
    yield Service()


def _is_active_event(event_name: str, event_type: str) -> bool:
    if not event_name or not event_type:
        return False

    return event_type.lower() != "inactive event"


def check_liebert_system_events(section: Section) -> CheckResult:
    active_events = [e for e in section["events"].items() if _is_active_event(*e)]

    if not active_events:
        yield Result(state=State.OK, summary="Normal")
        return

    yield from (Result(state=State.CRIT, summary=f"{k}: {v}") for k, v in active_events)


snmp_section_liebert_system_events = SimpleSNMPSection(
    name="liebert_system_events",
    parse_function=parse_liebert_system_events,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=[
            "10.1.2.100",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
            "20.1.2.100",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
        ],
    ),
    detect=DETECT_LIEBERT,
)

check_plugin_liebert_system_events = CheckPlugin(
    name="liebert_system_events",
    discovery_function=discover_liebert_system_events,
    check_function=check_liebert_system_events,
    service_name="System events",
)
