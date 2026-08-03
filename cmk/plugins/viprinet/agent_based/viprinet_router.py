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
from cmk.plugins.viprinet.lib import DETECT_VIPRINET


def parse_viprinet_router(string_table: StringTable) -> StringTable:
    return string_table


def discover_viprinet_router(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service(parameters={"mode_inv": section[0][0][0]})


def check_viprinet_router(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    router_mode_map = {
        "0": "Node",
        "1": "Hub",
        "2": "Hub running as HotSpare",
        "3": "Hotspare-Hub replacing another router",
    }
    expected_mode_map = {
        "node": "0",
        "hub": "1",
        "hub_hotspare": "2",
        "hub_hotspare_replacing": "3",
    }
    current_mode = section[0][0][0]
    mode = router_mode_map.get(current_mode)

    if expect_mode := params.get("expect_mode"):
        # Requires mode found on inventory
        expected_code = (
            params.get("mode_inv")
            if expect_mode == "inventory"
            else expected_mode_map.get(expect_mode)
        )
        if expected_code in router_mode_map and expected_code != current_mode:
            yield Result(
                state=State.CRIT,
                summary=f"Mode '{mode}' differs from expected mode '{router_mode_map.get(expected_code)}'",
            )
            return

    if mode:
        yield Result(state=State.OK, summary=mode)
        return

    yield Result(state=State.UNKNOWN, summary="Undefined Mode")


snmp_section_viprinet_router = SimpleSNMPSection(
    name="viprinet_router",
    detect=DETECT_VIPRINET,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.35424.1.1",
        oids=["5"],
    ),
    parse_function=parse_viprinet_router,
)


check_plugin_viprinet_router = CheckPlugin(
    name="viprinet_router",
    service_name="Router Mode",
    discovery_function=discover_viprinet_router,
    check_function=check_viprinet_router,
    check_ruleset_name="viprinet_router",
    check_default_parameters={},
)
