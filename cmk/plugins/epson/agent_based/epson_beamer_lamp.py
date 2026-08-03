#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)


def parse_epson_beamer_lamp(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_epson_beamer_lamp = SimpleSNMPSection(
    name="epson_beamer_lamp",
    parse_function=parse_epson_beamer_lamp,
    detect=contains(".1.3.6.1.2.1.1.2.0", "1248"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1248.4.1.1.1.1",
        oids=["0"],
    ),
)


def discover_epson_beamer_lamp(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_epson_beamer_lamp(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    lamp_time = int(section[0][0]) * 3600
    warn, crit = params["levels"]
    yield from check_levels(
        lamp_time,
        levels_upper=("fixed", (warn, crit)),
        render_func=lambda x: f"{x // 3600} h",
        label="Operation time",
    )


check_plugin_epson_beamer_lamp = CheckPlugin(
    name="epson_beamer_lamp",
    service_name="Beamer Lamp",
    discovery_function=discover_epson_beamer_lamp,
    check_function=check_epson_beamer_lamp,
    check_ruleset_name="lamp_operation_time",
    check_default_parameters={
        "levels": (1000 * 3600, 1500 * 3600),
    },
)
