#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.plugins.emc.lib import DETECT_DATADOMAIN
from cmk.plugins.lib.temperature import check_temperature, TempParamType

_STATUS_TABLE: Mapping[str, tuple[int, str]] = {
    "0": (2, "Failed"),
    "1": (0, "OK"),
    "2": (2, "Not found"),
    "3": (1, "Overheat Warning"),
    "4": (2, "Overheat Critical"),
}


def _format_emc_datadomain_temp(descr: str, encid: str, index: str, new_format: bool) -> str:
    if new_format:
        return f"{descr} Enclosure {encid}"
    return f"{encid}-{index}"


def parse_emc_datadomain_temps(string_table: StringTable) -> StringTable:
    return string_table


def discover_emc_datadomain_temps(section: StringTable) -> DiscoveryResult:
    for encid, index, descr, _reading, status in section:
        if status != "2":
            yield Service(item=_format_emc_datadomain_temp(descr, encid, index, True))


def check_emc_datadomain_temps(
    item: str, params: TempParamType, section: StringTable
) -> CheckResult:
    for encid, index, descr, reading, status in section:
        name = _format_emc_datadomain_temp(descr, encid, index, "Enclosure" in item)
        if item == name:
            dev_status, state_name = _STATUS_TABLE[status]
            yield from check_temperature(
                float(reading),
                params,
                unique_name=f"emc_datadomain_temps_{item}",
                value_store=get_value_store(),
                dev_status=dev_status,
                dev_status_name=state_name,
            )
            return


snmp_section_emc_datadomain_temps = SimpleSNMPSection(
    name="emc_datadomain_temps",
    parse_function=parse_emc_datadomain_temps,
    detect=DETECT_DATADOMAIN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19746.1.1.2.1.1.1",
        oids=["1", "2", "4", "5", "6"],
    ),
)


check_plugin_emc_datadomain_temps = CheckPlugin(
    name="emc_datadomain_temps",
    service_name="Temperature %s",
    discovery_function=discover_emc_datadomain_temps,
    check_function=check_emc_datadomain_temps,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
