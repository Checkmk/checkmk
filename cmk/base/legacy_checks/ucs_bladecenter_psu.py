#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.check_legacy_includes.temperature import check_temperature_list, CheckTempKwargs

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.plugins.lib import ucs_bladecenter

check_info = {}

# <<<ucs_bladecenter_psu:sep(9)>>>
# equipmentPsuInputStats  Dn sys/switch-A/psu-2/input-stats       Current 0.656250        PowerAvg 153.335938     Voltage 231.500000
# equipmentPsuStats       Dn sys/chassis-1/psu-1/stats    AmbientTemp 17.000000   Output12vAvg 12.008000  Output3v3Avg 3.336000


def ucs_bladecenter_psu_parse(string_table):
    data = ucs_bladecenter.generic_parse(string_table)
    psu: dict[str, dict] = {}

    def get_item_name(key):
        tokens = key.split("/")
        tokens[1] = tokens[1].replace("psu-", " Module ")
        tokens = [x[0].upper() + x[1:] for x in tokens]
        return "".join(tokens).replace("-", " ")

    for component, key_low, key_high in [
        ("equipmentPsuInputStats", 4, -12),
        ("equipmentPsuStats", 4, -6),
    ]:
        for key, values in data.get(component, {}).items():
            name = get_item_name(key[key_low:key_high])
            del values["Dn"]
            psu.setdefault(name, {}).update(values)

    return psu


# .
#   .--Chassis Volt.-------------------------------------------------------.
#   |         ____ _                   _      __     __    _ _             |
#   |        / ___| |__   __ _ ___ ___(_)___  \ \   / /__ | | |_           |
#   |       | |   | '_ \ / _` / __/ __| / __|  \ \ / / _ \| | __|          |
#   |       | |___| | | | (_| \__ \__ \ \__ \   \ V / (_) | | |_ _         |
#   |        \____|_| |_|\__,_|___/___/_|___/    \_/ \___/|_|\__(_)        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_ucs_bladecenter_psu(parsed):
    for key in parsed:
        if key.startswith("Chassis"):
            yield key, {}


def check_ucs_bladecenter_psu(item, params, parsed):
    if not (psu := parsed.get(item)):
        return
    value_3v = float(psu["Output3v3Avg"])
    value_12v = float(psu["Output12vAvg"])

    levels_3v = params["levels_3v_upper"] + params["levels_3v_lower"]
    levels_12v = params["levels_12v_upper"] + params["levels_12v_lower"]

    power_save_mode = value_3v == 0.0 and value_12v == 0.0

    yield check_levels(
        value_3v,
        "3_3v",
        None if power_save_mode else levels_3v,
        human_readable_func=lambda v: "%.2f V" % v,
        infoname="Output 3.3V-Average",
    )
    yield check_levels(
        value_12v,
        "12v",
        None if power_save_mode else levels_12v,
        human_readable_func=lambda v: "%.2f V" % v,
        infoname="Output 12V-Average",
    )

    if power_save_mode:
        yield 0, "Assuming 'Power Save Mode'"


check_info["ucs_bladecenter_psu"] = LegacyCheckDefinition(
    name="ucs_bladecenter_psu",
    parse_function=ucs_bladecenter_psu_parse,
    service_name="Voltage %s",
    discovery_function=inventory_ucs_bladecenter_psu,
    check_function=check_ucs_bladecenter_psu,
    check_ruleset_name="ucs_bladecenter_chassis_voltage",
    check_default_parameters={
        "levels_3v_lower": (3.25, 3.20),
        "levels_3v_upper": (3.4, 3.45),
        "levels_12v_lower": (11.9, 11.8),
        "levels_12v_upper": (12.1, 12.2),
    },
)

# .
#   .--Power Supply--------------------------------------------------------.
#   |    ____                          ____                    _           |
#   |   |  _ \ _____      _____ _ __  / ___| _   _ _ __  _ __ | |_   _     |
#   |   | |_) / _ \ \ /\ / / _ \ '__| \___ \| | | | '_ \| '_ \| | | | |    |
#   |   |  __/ (_) \ V  V /  __/ |     ___) | |_| | |_) | |_) | | |_| |    |
#   |   |_|   \___/ \_/\_/ \___|_|    |____/ \__,_| .__/| .__/|_|\__, |    |
#   |                                             |_|   |_|      |___/     |
#   '----------------------------------------------------------------------'


def inventory_ucs_bladecenter_psu_switch_power(parsed):
    for key in parsed:
        if key.startswith("Switch"):
            yield key, {}


def check_ucs_bladecenter_psu_switch_power(item, params, parsed):
    if not (psu := parsed.get(item)):
        return
    # Convert fields
    KEY_MAP = {"Current": "current", "PowerAvg": "power", "Voltage": "voltage"}

    psu_new = {}
    for k, v in psu.items():
        if k in KEY_MAP:
            k, v = KEY_MAP[k], (float(v), None)
        psu_new[k] = v

    yield from check_elphase(item, params, {item: psu_new})


check_info["ucs_bladecenter_psu.switch_power"] = LegacyCheckDefinition(
    name="ucs_bladecenter_psu_switch_power",
    service_name="Power Supply %s",
    sections=["ucs_bladecenter_psu"],
    discovery_function=inventory_ucs_bladecenter_psu_switch_power,
    check_function=check_ucs_bladecenter_psu_switch_power,
    check_ruleset_name="el_inphase",
)

# .
#   .--Temperature---------------------------------------------------------.
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def inventory_ucs_bladecenter_psu_chassis_temp(parsed):
    for key, values in parsed.items():
        if key.startswith("Chassis") and values.get("AmbientTemp"):
            yield "Ambient " + " ".join(key.split()[:2]), {}


def check_ucs_bladecenter_psu_chassis_temp(item, params, parsed):
    sensor_item = item[8:]  # drop "Ambient "
    sensor_list: list[tuple[str, float, CheckTempKwargs]] = [
        ("Module %s" % key.split()[-1], float(values.get("AmbientTemp")), {})
        for key, values in sorted(parsed.items())
        if key.startswith(sensor_item) and "AmbientTemp" in values
    ]
    yield from check_temperature_list(sensor_list, params)


check_info["ucs_bladecenter_psu.chassis_temp"] = LegacyCheckDefinition(
    name="ucs_bladecenter_psu_chassis_temp",
    service_name="Temperature %s",
    sections=["ucs_bladecenter_psu"],
    discovery_function=inventory_ucs_bladecenter_psu_chassis_temp,
    check_function=check_ucs_bladecenter_psu_chassis_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (35.0, 40.0),
    },
)
