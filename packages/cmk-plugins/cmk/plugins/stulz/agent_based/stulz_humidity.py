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
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.stulz.lib import DETECT_STULZ


def _savefloat(f: str) -> float:
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


Section = Mapping[str, str]


def parse_stulz_humidity(string_table: StringTable) -> Section:
    parsed: dict[str, str] = {}
    for oidend, value in string_table:
        bus, unit = oidend.split(".")[0:2]
        parsed.setdefault(f"{bus}-{unit}", value)
    return parsed


def discover_stulz_humidity(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_stulz_humidity(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if item in section:
        yield from check_humidity(_savefloat(section[item]) / 10, params)


snmp_section_stulz_humidity = SimpleSNMPSection(
    name="stulz_humidity",
    detect=DETECT_STULZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.29462.10.2.1.1.1.1.2.1.1",
        oids=[OIDEnd(), "1194"],
    ),
    parse_function=parse_stulz_humidity,
)

check_plugin_stulz_humidity = CheckPlugin(
    name="stulz_humidity",
    service_name="Humidity %s ",
    discovery_function=discover_stulz_humidity,
    check_function=check_stulz_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (60.0, 65.0),
        "levels_lower": (40.0, 35.0),
    },
)
