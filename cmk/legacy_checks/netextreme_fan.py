#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

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
from cmk.plugins.lib.fan import check_fan
from cmk.plugins.netextreme.lib import DETECT_NETEXTREME

# Just an assumption, levels as in other fan checks


def discover_netextreme_fan(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=line[0]) for line in section)


def check_netextreme_fan(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    map_fan_status = {
        "1": (State.OK, "on"),
        "2": (State.OK, "off"),
    }
    for fan_nr, fan_status, fan_speed_str in section:
        if fan_nr == item:
            state, state_readable = map_fan_status[fan_status]
            yield Result(state=state, summary=f"Operational status: {state_readable}")
            if fan_speed_str:
                yield from check_fan(int(fan_speed_str), params)


def parse_netextreme_fan(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_netextreme_fan = SimpleSNMPSection(
    name="netextreme_fan",
    parse_function=parse_netextreme_fan,
    detect=DETECT_NETEXTREME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.1.1.9.1",
        oids=["1", "2", "4"],
    ),
)


check_plugin_netextreme_fan = CheckPlugin(
    name="netextreme_fan",
    service_name="Fan %s",
    discovery_function=discover_netextreme_fan,
    check_function=check_netextreme_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (2000, 1000),
        "upper": (8000, 8400),
    },
)
