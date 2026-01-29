#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import (
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
)
from cmk.agent_based.v2 import equals, SNMPTree, StringTable
from cmk.base.check_legacy_includes.elphase import check_elphase

check_info = {}

# .1.3.6.1.4.1.13742.4.1.2.2.1.1.1 1 --> PDU-MIB::outletIndex.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.1.3 3 --> PDU-MIB::outletIndex.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.1.4 4 --> PDU-MIB::outletIndex.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.2.1 Outlet 1 --> PDU-MIB::outletLabel.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.2.3 Outlet 3 --> PDU-MIB::outletLabel.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.2.4 Outlet 4 --> PDU-MIB::outletLabel.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.3.1 1 --> PDU-MIB::outletOperationalState.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.3.3 1 --> PDU-MIB::outletOperationalState.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.3.4 0 --> PDU-MIB::outletOperationalState.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.4.1 0 --> PDU-MIB::outletCurrent.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.4.3 6854 --> PDU-MIB::outletCurrent.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.4.4 0 --> PDU-MIB::outletCurrent.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.6.1 222000 --> PDU-MIB::outletVoltage.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.6.3 222000 --> PDU-MIB::outletVoltage.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.6.4 222000 --> PDU-MIB::outletVoltage.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.7.1 0 --> PDU-MIB::outletActivePower.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.7.3 1475 --> PDU-MIB::outletActivePower.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.7.4 0 --> PDU-MIB::outletActivePower.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.8.1 0 --> PDU-MIB::outletApparentPower.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.8.3 1542 --> PDU-MIB::outletApparentPower.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.8.4 0 --> PDU-MIB::outletApparentPower.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.31.1 0 --> PDU-MIB::outletWattHours.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.31.3 0 --> PDU-MIB::outletWattHours.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.31.4 0 --> PDU-MIB::outletWattHours.4


def parse_raritan_px_outlets(string_table: StringTable) -> dict[str, Any]:
    map_state = {
        "-1": (2, "error"),
        "0": (2, "off"),
        "1": (0, "on"),
        "2": (0, "cycling"),
    }
    parsed = {}
    for (
        index,
        label,
        state,
        current_str,
        voltage_str,
        power_str,
        appower_str,
        energy_str,
    ) in string_table:
        parsed[index] = {
            "device_state": map_state.get(state, (3, "unknown")),
            "label": label,
            "current": float(current_str) / 1000,
            "voltage": float(voltage_str) / 1000,
            "power": float(power_str),
            "appower": float(appower_str),
            "energy": float(energy_str),
        }

    return parsed


def discover_raritan_px_outlets(parsed: dict[str, Any]) -> LegacyDiscoveryResult:
    return [(index, {}) for index, values in parsed.items() if values["device_state"][1] == "on"]


def check_raritan_px_outlets(
    item: str, params: Mapping[str, Any], parsed: dict[str, Any]
) -> LegacyCheckResult:
    if item in parsed:
        if parsed[item]["label"]:
            yield 0, "[%s]" % parsed[item]["label"]
        yield from check_elphase(item, params, parsed)


check_info["raritan_px_outlets"] = LegacyCheckDefinition(
    name="raritan_px_outlets",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.4"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.4.1.2.2.1",
        oids=["1", "2", "3", "4", "6", "7", "8", "31"],
    ),
    parse_function=parse_raritan_px_outlets,
    service_name="Outlet %s",
    discovery_function=discover_raritan_px_outlets,
    check_function=check_raritan_px_outlets,
    check_ruleset_name="el_inphase",
)
