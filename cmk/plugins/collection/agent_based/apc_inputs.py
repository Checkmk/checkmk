#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
from cmk.plugins.lib.apc import DETECT


def inventory_apc_inputs(section: StringTable) -> DiscoveryResult:
    yield from (
        Service(item=line[0], parameters={"state": line[2]})
        for line in section
        if line[2] not in ["3", "4"]
    )


def check_apc_inputs(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    states = {
        "1": "closed",
        "2": "open",
        "3": "disabled",
        "4": "not applicable",
    }
    alarm_states = {
        "1": "normal",
        "2": "warning",
        "3": "critical",
        "4": "not applicable",
    }
    for name, _location, state, alarm_status in section:
        if name == item:
            match alarm_status:
                case "2" | "4":
                    check_state = State.WARN
                case "3":
                    check_state = State.CRIT
                case "1":
                    check_state = State.OK

            yield Result(state=check_state, summary="State is %s" % alarm_states[alarm_status])

            if params["state"] != state:
                yield Result(
                    state=State.WARN,
                    summary="Port state Change from {} to {}".format(
                        states[params["state"]], states[state]
                    ),
                )

            return


def parse_apc_inputs(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_apc_inputs = SimpleSNMPSection(
    name="apc_inputs",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.25.2.2.1",
        oids=["3", "4", "5", "6"],
    ),
    parse_function=parse_apc_inputs,
)
check_plugin_apc_inputs = CheckPlugin(
    name="apc_inputs",
    service_name="Input %s",
    discovery_function=inventory_apc_inputs,
    check_function=check_apc_inputs,
    check_default_parameters={},
)
