#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}


def parse_orion_system(string_table):
    if not string_table:
        return None

    # states do not belong to the parsing :-(
    map_charge_states = {
        "1": (0, "float charging"),
        "2": (0, "discharge"),
        "3": (0, "equalize"),
        "4": (0, "boost"),
        "5": (0, "battery test"),
        "6": (0, "recharge"),
        "7": (0, "separate charge"),
        "8": (0, "event control charge"),
    }

    (
        system_voltage,
        load_current,
        battery_current,
        battery_temp,
        charge_state,
        _battery_current_limit,
        rectifier_current,
        system_power,
    ) = string_table[0]

    temperature = dict[str, float]()
    if battery_temp != "2147483647":
        # From MIB: The max. value 2147483647 is used to indicate an invalid value."
        temperature["Battery"] = int(battery_temp) * 0.1

    electrical = dict[str, dict[str, float]]()
    for what, value, factor in [
        ("voltage", system_voltage, 0.01),
        ("current", load_current, 0.1),
        ("power", system_power, 1),
    ]:
        if value != "2147483647":
            # From MIB: The max. value 2147483647 is used to indicate an invalid value."
            system_data = electrical.setdefault("System", {})
            system_data[what] = int(value) * factor

    for item, value in [
        ("Battery", battery_current),
        ("Rectifier", rectifier_current),
    ]:
        if value != "2147483647":
            # From MIB: The max. value 2147483647 is used to indicate an invalid value."
            item_data = electrical.setdefault(item, {})
            item_data["current"] = int(battery_temp) * 0.1

    return {
        "charging": {
            "Battery": map_charge_states.get(charge_state, (3, "unknown[%s]" % charge_state))
        },
        "temperature": temperature,
        "electrical": electrical,
    }


def discover_orion_system_temp(parsed):
    for entity in parsed["temperature"]:
        yield entity, {}


def check_orion_system_temp(item, params, parsed):
    if item in parsed["temperature"]:
        return check_temperature(parsed["temperature"][item], params, "orion_system_temp.%s" % item)
    return None


check_info["orion_system"] = LegacyCheckDefinition(
    name="orion_system",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20246"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20246.2.3.1.1.1.2.3",
        oids=["1", "2", "3", "4", "5", "6", "7", "8"],
    ),
    parse_function=parse_orion_system,
    service_name="Temperature %s",
    discovery_function=discover_orion_system_temp,
    check_function=check_orion_system_temp,
    check_ruleset_name="temperature",
)


def discover_orion_system_charging(parsed):
    for entity in parsed["charging"]:
        yield entity, {}


def check_orion_system_charging(item, params, parsed):
    if item in parsed["charging"]:
        state, state_readable = parsed["charging"][item]
        return state, "Status: %s" % state_readable
    return None


check_info["orion_system.charging"] = LegacyCheckDefinition(
    name="orion_system_charging",
    service_name="Charge %s",
    sections=["orion_system"],
    discovery_function=discover_orion_system_charging,
    check_function=check_orion_system_charging,
)


def discover_orion_system_electrical(parsed):
    for entity in parsed["electrical"]:
        yield entity, {}


def check_orion_system_electrical(item, params, parsed):
    return check_elphase(item, params, parsed["electrical"])


check_info["orion_system.dc"] = LegacyCheckDefinition(
    name="orion_system_dc",
    service_name="Direct Current %s",
    sections=["orion_system"],
    discovery_function=discover_orion_system_electrical,
    check_function=check_orion_system_electrical,
    check_ruleset_name="ups_outphase",
)
