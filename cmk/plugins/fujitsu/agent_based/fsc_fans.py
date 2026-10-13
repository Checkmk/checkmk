#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    exists,
    not_exists,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.plugins.lib.fan import check_fan


def parse_fsc_fans(string_table: StringTable) -> Mapping[str, int]:
    parsed: dict[str, int] = {}
    for fan_name, rpm_str in string_table:
        try:
            rpm = int(rpm_str)
        except ValueError:
            continue
        parsed.setdefault(fan_name, rpm)
    return parsed


def discover_fsc_fans(section: Mapping[str, int]) -> DiscoveryResult:
    yield from (Service(item=fan_name) for fan_name in section)


def check_fsc_fans(item: str, params: Mapping[str, Any], section: Mapping[str, int]) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield from check_fan(data, params)


snmp_section_fsc_fans = SimpleSNMPSection(
    name="fsc_fans",
    detect=all_of(
        all_of(
            any_of(
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.231"),
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.311"),
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072"),
            ),
            exists(".1.3.6.1.4.1.231.2.10.2.1.1.0"),
        ),
        not_exists(".1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.*"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.5.2.2.1",
        oids=["16", "8"],
    ),
    parse_function=parse_fsc_fans,
)


check_plugin_fsc_fans = CheckPlugin(
    name="fsc_fans",
    service_name="FSC %s",
    discovery_function=discover_fsc_fans,
    check_function=check_fsc_fans,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (2000, 1000),
    },
)
