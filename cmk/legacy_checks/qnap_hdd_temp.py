#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.qnap.lib import DETECT_QNAP


def parse_qnap_hdd_temp(string_table: StringTable) -> Mapping[str, float]:
    parsed: dict[str, float] = {}
    for hdd, temp in string_table:
        with contextlib.suppress(ValueError):
            parsed[hdd] = float(temp.split()[0])
    return parsed


def check_qqnap_hdd_temp(
    item: str, params: TempParamType, section: Mapping[str, float]
) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield from check_temperature(
        reading=data,
        params=params,
        unique_name=item,
        value_store=get_value_store(),
    )


def discover_qnap_hdd_temp(section: Mapping[str, float]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_qnap_hdd_temp = SimpleSNMPSection(
    name="qnap_hdd_temp",
    detect=DETECT_QNAP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.24681.1.2.11.1",
        oids=["2", "3"],
    ),
    parse_function=parse_qnap_hdd_temp,
)


check_plugin_qnap_hdd_temp = CheckPlugin(
    name="qnap_hdd_temp",
    service_name="QNAP %s Temperature",
    discovery_function=discover_qnap_hdd_temp,
    check_function=check_qqnap_hdd_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (40.0, 45.0),
    },
)
