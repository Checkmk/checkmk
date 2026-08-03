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
    equals,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.fan import check_fan


def parse_climaveneta_fan(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_climaveneta_fan = SimpleSNMPSection(
    name="climaveneta_fan",
    parse_function=parse_climaveneta_fan,
    detect=equals(".1.3.6.1.2.1.1.1.0", "pCO Gateway"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9839.2.1.2",
        oids=["42", "43"],
    ),
)


def discover_climaveneta_fan(section: StringTable) -> DiscoveryResult:
    if section and len(section[0]) == 2:
        yield Service(item="1")
        yield Service(item="2")


def check_climaveneta_fan(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    rpm = int(section[0][int(item) - 1])
    yield from check_fan(rpm, params)


check_plugin_climaveneta_fan = CheckPlugin(
    name="climaveneta_fan",
    service_name="Fan %s",
    discovery_function=discover_climaveneta_fan,
    check_function=check_climaveneta_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (200, 100),
    },
)
