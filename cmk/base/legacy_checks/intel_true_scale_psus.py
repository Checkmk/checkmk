#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.intel import DETECT_INTEL_TRUE_SCALE

# .1.3.6.1.4.1.10222.2.1.4.7.1.2.2.1 Power Supply 201 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyDescription.2.1
# .1.3.6.1.4.1.10222.2.1.4.7.1.2.3.2 Power Supply 202 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyDescription.3.2
# .1.3.6.1.4.1.10222.2.1.4.7.1.2.4.3 Power Supply 203 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyDescription.4.3
# .1.3.6.1.4.1.10222.2.1.4.7.1.2.5.4 Power Supply 204 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyDescription.5.4
# .1.3.6.1.4.1.10222.2.1.4.7.1.3.2.1 6 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOperStatus.2.1
# .1.3.6.1.4.1.10222.2.1.4.7.1.3.3.2 6 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOperStatus.3.2
# .1.3.6.1.4.1.10222.2.1.4.7.1.3.4.3 6 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOperStatus.4.3
# .1.3.6.1.4.1.10222.2.1.4.7.1.3.5.4 6 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOperStatus.5.4
# .1.3.6.1.4.1.10222.2.1.4.7.1.4.2.1 1 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyInputSource.2.1
# .1.3.6.1.4.1.10222.2.1.4.7.1.4.3.2 1 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyInputSource.3.2
# .1.3.6.1.4.1.10222.2.1.4.7.1.4.4.3 1 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyInputSource.4.3
# .1.3.6.1.4.1.10222.2.1.4.7.1.4.5.4 1 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyInputSource.5.4
# .1.3.6.1.4.1.10222.2.1.4.7.1.5.2.1 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyVoltage.2.1
# .1.3.6.1.4.1.10222.2.1.4.7.1.5.3.2 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyVoltage.3.2
# .1.3.6.1.4.1.10222.2.1.4.7.1.5.4.3 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyVoltage.4.3
# .1.3.6.1.4.1.10222.2.1.4.7.1.5.5.4 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyVoltage.5.4
# .1.3.6.1.4.1.10222.2.1.4.7.1.6.2.1 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOutputPower.2.1
# .1.3.6.1.4.1.10222.2.1.4.7.1.6.3.2 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOutputPower.3.2
# .1.3.6.1.4.1.10222.2.1.4.7.1.6.4.3 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOutputPower.4.3
# .1.3.6.1.4.1.10222.2.1.4.7.1.6.5.4 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOutputPower.5.4


def parse_intel_true_scale_psus(info):
    map_states = {
        "1": (3, "unknown"),
        "2": (3, "disabled"),
        "3": (2, "failed"),
        "4": (1, "warning"),
        "5": (0, "standby"),
        "6": (0, "engaged"),
        "7": (0, "redundant"),
        "8": (3, "not present"),
    }
    map_sources = {
        "0": "invalid",
        "1": "ac line",
        "2": "dc line",
        "3": "none",
        "4": "unknown",
    }

    parsed = {}
    for descr, operstate, source, voltage_str, power_str in info:
        name = descr.replace("Power Supply", "").strip()

        parsed.setdefault(
            name,
            {
                "voltage": float(voltage_str),
                "power": float(power_str),
                "state": map_states[operstate],
                "source": map_sources[source],
            },
        )

    return parsed


def inventory_intel_true_scale_psus(parsed):
    for psu in parsed:
        if parsed[psu]["state"][-1] not in ["not present", "disabled"]:
            yield psu, {}


def check_intel_true_scale_psus(item, params, parsed):
    if item in parsed:
        state, state_readable = parsed[item]["state"]
        yield state, "Operational status: %s, Source: %s" % (state_readable, parsed[item]["source"])

        for res in check_elphase(item, params, parsed):
            yield res


check_info["intel_true_scale_psus"] = {
    "detect": DETECT_INTEL_TRUE_SCALE,
    "parse_function": parse_intel_true_scale_psus,
    "discovery_function": inventory_intel_true_scale_psus,
    "check_function": check_intel_true_scale_psus,
    "service_name": "Power supply %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.10222.2.1.4.7.1",
        oids=["2", "3", "4", "5", "6"],
    ),
    "check_ruleset_name": "el_inphase",
}
