#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
)
from cmk.plugins.hwg.agent_based.lib import parse_hwg
from cmk.plugins.lib.humidity import check_humidity

HWG_HUMIDITY_DEFAULTLEVELS = {"levels": (60.0, 70.0)}


def discover_hwg_humidity(
    section: Mapping[str, Mapping[str, Any]],
) -> DiscoveryResult:
    for index, attrs in section.items():
        if attrs.get("humidity"):
            yield Service(item=index)


def check_hwg_humidity(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    if not (data := section.get(item)):
        return

    yield from check_humidity(data["humidity"], params)
    yield Result(
        state=State.OK,
        summary=f"Description: {data['descr']}, Status: {data['dev_status_name']}",
    )


snmp_section_hwg_humidity = SimpleSNMPSection(
    name="hwg_humidity",
    detect=contains(".1.3.6.1.2.1.1.1.0", "hwg"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21796.4.1.3.1",
        oids=["1", "2", "3", "4", "7"],
    ),
    parse_function=parse_hwg,
)


check_plugin_hwg_humidity = CheckPlugin(
    name="hwg_humidity",
    service_name="Humidity %s",
    discovery_function=discover_hwg_humidity,
    check_function=check_hwg_humidity,
    check_ruleset_name="humidity",
    check_default_parameters=HWG_HUMIDITY_DEFAULTLEVELS,
)


check_plugin_hwg_ste2_humidity = CheckPlugin(
    name="hwg_ste2_humidity",
    service_name="Humidity %s",
    sections=["hwg_ste2"],
    discovery_function=discover_hwg_humidity,
    check_function=check_hwg_humidity,
    check_ruleset_name="humidity",
    check_default_parameters=HWG_HUMIDITY_DEFAULTLEVELS,
)
