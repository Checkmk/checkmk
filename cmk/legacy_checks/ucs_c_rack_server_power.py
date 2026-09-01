#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# exemplary output of special agent agent_ucs_bladecenter (separator is <TAB> and means tabulator):
#
# <<<ucs_c_rack_server_motherboard_power:sep(9)>>>
# computeMbPowerStats<TAB>dn sys/rack-unit-1/board/power-stats<TAB>consumedPower 88<TAB>inputCurrent 6.00<TAB>inputVoltage 12.100
# computeMbPowerStats<TAB>dn sys/rack-unit-2/board/power-stats<TAB>consumedPower 88<TAB>inputCurrent 6.00<TAB>inputVoltage 12.100

# Default values for consumed power selected according to exemplary monitored real world values
# of a rack servers motherboards. Reasonable values for the actual use case depend on the rack
# servers configuration (racks used in rack server) and require customization via WATO rule.


import contextlib
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
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

type Section = Mapping[str, Mapping[str, float]]


def parse_ucs_c_rack_server_power(string_table: StringTable) -> Section:
    """
    Returns dict with indexed rack motherboards mapped to keys and consumed power,
    input current status and input voltage status as value.
    """
    parsed: dict[str, dict[str, float]] = {}
    # The element count of string_table lines is under our control (agent output) and
    # ensured to have expected length. It is ensured that elements contain a
    # string. Values which the XML API reports in a form we cannot cast are left out.
    for _, dn, power, current, voltage in string_table:
        motherboard = (
            dn.replace("dn ", "")
            .replace("sys/", "")
            .replace("rack-unit-", "Rack Unit ")
            .replace("/board", "")
            .replace("/power-stats", "")
        )
        parsed.setdefault(motherboard, {})
        for ds_key, ds in (
            ("consumedPower", power),  # consumedPower is no longer int but float instead!!
            ("inputCurrent", current),
            ("inputVoltage", voltage),
        ):
            with contextlib.suppress(ValueError):
                parsed[motherboard][ds_key] = float(ds.replace(ds_key + " ", ""))
    return parsed


def discover_ucs_c_rack_server_power(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_ucs_c_rack_server_power(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return

    yield from check_levels(
        data["consumedPower"],
        "power",
        params["power_upper_levels"],
        human_readable_func=lambda x: f"{x:.1f} W",
        infoname="Power",
    )
    yield Result(state=State.OK, summary=f"Current: {data['inputCurrent']} A")
    yield Result(state=State.OK, summary=f"Voltage: {data['inputVoltage']} V")


agent_section_ucs_c_rack_server_power = AgentSection(
    name="ucs_c_rack_server_power",
    parse_function=parse_ucs_c_rack_server_power,
)


check_plugin_ucs_c_rack_server_power = CheckPlugin(
    name="ucs_c_rack_server_power",
    service_name="Motherboard Power Statistics %s",
    discovery_function=discover_ucs_c_rack_server_power,
    check_function=check_ucs_c_rack_server_power,
    check_ruleset_name="power_multiitem",
    check_default_parameters={
        "power_upper_levels": (90, 100),
    },
)
