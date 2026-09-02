#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass
from typing import ReadOnly, TypedDict

from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.raritan.lib import PLUG_STATE_MAPPING


@dataclass(frozen=True, kw_only=True)
class Plug:
    state: str
    outlet_name: str


type Section = Mapping[str, Plug]


class CombinedParams(TypedDict, total=False):
    required_state: ReadOnly[str | None]
    discovered_state: ReadOnly[str]


def parse_raritan_pdu_plugs(string_table: StringTable) -> Section:
    return {
        outlet_label: Plug(
            state=PLUG_STATE_MAPPING.get(outlet_state, "unknown"),
            outlet_name=outlet_name,
        )
        for outlet_label, outlet_name, outlet_state in string_table
    }


def discover_raritan_pdu_plugs(section: Section) -> DiscoveryResult:
    for key, plug in section.items():
        if plug.state != "unknown":
            yield Service(item=key, parameters={"discovered_state": plug.state})


def check_raritan_pdu_plugs(item: str, params: CombinedParams, section: Section) -> CheckResult:
    if (plug := section.get(item)) is None:
        return

    if plug.outlet_name:
        yield Result(state=State.OK, summary=plug.outlet_name)

    expected_state = params["required_state"] or params["discovered_state"]

    if plug.state != expected_state:
        yield Result(state=State.CRIT, summary=f"Status: {plug.state} (expected: {expected_state})")
    else:
        yield Result(state=State.OK, summary=f"Status: {plug.state}")


snmp_section_raritan_pdu_plugs = SimpleSNMPSection(
    name="raritan_pdu_plugs",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.6"),
        any_of(
            startswith(".1.3.6.1.4.1.13742.6.3.2.1.1.3.1", "PX2-2"),
            startswith(".1.3.6.1.4.1.13742.6.3.2.1.1.3.1", "PX3"),
        ),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6",
        oids=["3.5.3.1.2", "3.5.3.1.3", "4.1.2.1.3"],
    ),
    parse_function=parse_raritan_pdu_plugs,
)


check_plugin_raritan_pdu_plugs = CheckPlugin(
    name="raritan_pdu_plugs",
    service_name="Plug %s",
    discovery_function=discover_raritan_pdu_plugs,
    check_function=check_raritan_pdu_plugs,
    check_ruleset_name="plugs",
    check_default_parameters={"required_state": None},
)
