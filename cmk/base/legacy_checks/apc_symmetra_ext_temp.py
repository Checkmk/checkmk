#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyResult
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature, TempParamType
from cmk.plugins.apc.lib_ats import DETECT

check_info = {}


def discover_apc_symmetra_ext_temp(info: StringTable) -> Iterable[tuple[str, dict[str, Any]]]:
    for index, status, _temp, _temp_unit in info:
        if status == "2":
            yield index, {}


def check_apc_symmetra_ext_temp(
    item: str, params: TempParamType, info: StringTable
) -> LegacyResult:
    for index, _status, temp, temp_unit in info:
        if item == index:
            unit = "f" if temp_unit == "2" else "c"
            return check_temperature(
                int(temp), params, "apc_symmetra_ext_temp_%s" % item, dev_unit=unit
            )

    return 3, "Sensor not found in SNMP data"


def parse_apc_symmetra_ext_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["apc_symmetra_ext_temp"] = LegacyCheckDefinition(
    name="apc_symmetra_ext_temp",
    parse_function=parse_apc_symmetra_ext_temp,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.10.2.3.2.1",
        oids=["1", "3", "4", "5"],
    ),
    service_name="Temperature External %s",
    discovery_function=discover_apc_symmetra_ext_temp,
    check_function=check_apc_symmetra_ext_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (30.0, 35.0)},
)
