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
from cmk.plugins.lib.apc import DETECT

# .1.3.6.1.4.1.318.1.1.13.3.1.2.1.3.1 Power Source B Failure
# .1.3.6.1.4.1.318.1.1.13.3.1.2.1.3.2 Fan Power Supply Right Fault


class Section(TypedDict, total=True):
    events: tuple[str, ...]


def parse_apc_inrow_system_events(string_table: StringTable) -> Section:
    return {"events": tuple(first_word for first_word, *_rest in string_table)}


def discover_apc_inrow_system_events(section: Section) -> DiscoveryResult:
    yield Service()


def check_apc_inrow_system_events(params: Mapping[str, int], section: Section) -> CheckResult:
    if events := section["events"]:
        yield from (Result(state=State(params["state"]), summary=event) for event in events)
        return

    yield Result(state=State.OK, summary="No service events")


snmp_section_apc_inrow_system_events = SimpleSNMPSection(
    name="apc_inrow_system_events",
    parse_function=parse_apc_inrow_system_events,
    fetch=SNMPTree(base=".1.3.6.1.4.1.318.1.1.13.3.1.2.1", oids=["3"]),  # airIRAlarmDescription
    detect=DETECT,
)

check_plugin_apc_inrow_system_events = CheckPlugin(
    name="apc_inrow_system_events",
    discovery_function=discover_apc_inrow_system_events,
    check_function=check_apc_inrow_system_events,
    check_default_parameters={"state": 2},
    service_name="System events",
    check_ruleset_name="apc_system_events",
)
