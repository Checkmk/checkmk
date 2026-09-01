#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# exemplary output of special agent agent_ucs_bladecenter (<TAB> is tabulator):
#
# <<<ucs_c_rack_server_psu:sep(9)>>>
# equipmentPsu<TAB>dn  sys/rack-unit-1/psu-1<TAB>id 1<TAB>model blabla<TAB>operability operable<TAB>voltage upper-critical
# equipmentPsu<TAB>dn sys/rack-unit-1/psu-2 <TAB>id 2<TAB>model blabla<TAB>operability inoperable<TAB>voltage ok


from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


@dataclass(frozen=True, kw_only=True)
class Psu:
    operability: str
    voltage: str
    model: str


type Section = Mapping[str, Psu]

# maps XML API v2.0 XML entity values to check function states
_OPERABILITY_TO_STATE = {
    "unknown": State.UNKNOWN,
    "operable": State.OK,
    "inoperable": State.CRIT,
    "degraded": State.CRIT,
    "powered-off": State.WARN,
    "power-problem": State.CRIT,
    "removed": State.WARN,
    "voltage-problem": State.CRIT,
    "thermal-problem": State.CRIT,
    "performance-problem": State.CRIT,
    "accessibility-problem": State.CRIT,
    "identity-unestablishable": State.WARN,
    "bios-post-timeout": State.WARN,
    "disabled": State.WARN,
    "malformed-fru": State.WARN,
    "fabric-conn-problem": State.CRIT,
    "fabric-unsupported-conn": State.WARN,
    "config": State.WARN,
    "equipment-problem": State.CRIT,
    "decomissioning": State.WARN,
    "chassis-limit-exceeded": State.WARN,
    "not-supported": State.WARN,
    "discovery": State.WARN,
    "discovery-failed": State.WARN,
    "identify": State.WARN,
    "post-failure": State.WARN,
    "upgrade-problem": State.WARN,
    "peer-comm-problem": State.CRIT,
    "auto-upgrade": State.WARN,
}

# maps XML API v2.0 XML entity values to check function states
_VOLTAGE_TO_STATE = {
    "unknown": State.UNKNOWN,
    "ok": State.OK,
    "upper-non-recoverable": State.CRIT,
    "upper-critical": State.CRIT,
    "upper-non-critical": State.WARN,
    "lower-non-critical": State.WARN,
    "lower-critical": State.CRIT,
    "lower-non-recoverable": State.CRIT,
    "not-supported": State.WARN,
}


def parse_ucs_c_rack_server_psu(string_table: StringTable) -> Section:
    """
    Returns dict with indexed PSUs mapped to keys and operability, voltage and model as value.
    """
    parsed = {}
    for psu in string_table:
        try:
            key_value_pairs = [kv.split(" ", 1) for kv in psu[1:]]
            item = (
                key_value_pairs[0][1]
                .replace("sys/", "")
                .replace("rack-unit-", "Rack Unit ")
                .replace("/psu-", " PSU ")
            )
            parsed[item] = Psu(
                operability=key_value_pairs[3][1],
                voltage=key_value_pairs[4][1],
                model=key_value_pairs[2][1],
            )
        except IndexError:
            continue  # skip string_table line in case agent output is incomplete or invalid
    return parsed


agent_section_ucs_c_rack_server_psu = AgentSection(
    name="ucs_c_rack_server_psu",
    parse_function=parse_ucs_c_rack_server_psu,
)


#########################
# ucs_c_rack_server_psu #
#########################


def discover_ucs_c_rack_server_psu(section: Section) -> DiscoveryResult:
    """
    Yields indexed PSUs as items (e.g. Rack Unit 1 PSU 1).
    """
    yield from (Service(item=item) for item in section)


def check_ucs_c_rack_server_psu(item: str, section: Section) -> CheckResult:
    if (psu := section.get(item)) is None:
        return

    if (state := _OPERABILITY_TO_STATE.get(psu.operability)) is None:
        yield Result(state=State.UNKNOWN, summary=f"Status: unknown[{psu.operability}]")
    else:
        yield Result(state=state, summary=f"Status: {psu.operability}")


check_plugin_ucs_c_rack_server_psu = CheckPlugin(
    name="ucs_c_rack_server_psu",
    service_name="Output Power %s",
    discovery_function=discover_ucs_c_rack_server_psu,
    check_function=check_ucs_c_rack_server_psu,
)

#################################
# ucs_c_rack_server_psu.voltage #
#################################


def discover_ucs_c_rack_server_psu_voltage(section: Section) -> DiscoveryResult:
    for item, psu in section.items():
        if psu.voltage == "unknown" and psu.model.startswith("UCS-"):
            continue  # see SUP-11285
        yield Service(item=item)


def check_ucs_c_rack_server_psu_voltage(item: str, section: Section) -> CheckResult:
    if (psu := section.get(item)) is None:
        return

    if (state := _VOLTAGE_TO_STATE.get(psu.voltage)) is None:
        yield Result(state=State.UNKNOWN, summary=f"Status: unknown[{psu.voltage}]")
    else:
        yield Result(state=state, summary=f"Status: {psu.voltage}")


check_plugin_ucs_c_rack_server_psu_voltage = CheckPlugin(
    name="ucs_c_rack_server_psu_voltage",
    service_name="Output Voltage %s",
    sections=["ucs_c_rack_server_psu"],
    discovery_function=discover_ucs_c_rack_server_psu_voltage,
    check_function=check_ucs_c_rack_server_psu_voltage,
)
