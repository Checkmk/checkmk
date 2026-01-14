#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, contains, OIDBytes, OIDEnd, SNMPTree, startswith
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

_TABLES = ["1", "2", "3", "4"]


def parse_emka_modules(string_table):
    if not any(string_table):
        return None

    # basModuleCoIx == 0
    map_module_types = {
        "0": "vacant",
        "8": "U8, keypad",
        "9": "U9, card module (proximity)",
        "10": "U10, phone module (modem)",
        "11": "U11/U32, up to 8 handles / single point latches",
        "12": "U12/U33, up to 2 handles / single point latches",
        "13": "U13, 4 sensors and 4 relays",
        "14": "U14, communication module",
        "15": "fultifunction module M15",
        "16": "fultifunction module M16",
    }

    # independent of module type, basModuleCoIx > 0
    map_component_types = {
        "1": "alarm",
        "2": "handle",
        "3": "sensor",
        "4": "relay",
        "5": "keypad",
        "6": "card_terminal",
        "7": "phone_modem",
        "8": "analogous_output",
    }

    parsed: dict = {"basic_components": {}}
    for oidend, status, ty, mod_info, remark in string_table[0]:
        mo_index, co_index = oidend.split(".")
        if mo_index == "0":
            itemname = "Master %s" % mod_info.split(",")[0]
        else:
            itemname = f"Perip {mo_index} {mod_info}"

        if co_index == "0":
            parsed["basic_components"].setdefault(
                itemname.strip(),
                {
                    "type": map_module_types[co_index],
                    "activation": status,
                    "_location_": "0.%s" % mo_index,
                },
            )
            continue

        table = map_component_types[ty]
        if remark == "":
            itemname = oidend
        else:
            itemname = f"{remark} {oidend}"

        parsed.setdefault(table, {})
        parsed[table].setdefault(itemname, {"_location_": oidend})

    for table_idx, block in zip(_TABLES, string_table[1:5]):
        for module_link, value, mode in block:
            table = map_component_types[table_idx]
            location = ".".join(module_link.split(".")[-2:])
            for entry, attrs in list(parsed.get(table, {}).items()):
                item_location = attrs["_location_"]
                if item_location != location:
                    continue

                attrs["value"] = value
                if mode:
                    attrs["mode"] = mode

    for oidend, threshold in string_table[5]:
        location, threshold_ty = oidend.split(".")
        if threshold_ty == "1":
            ty = "levels_lower"
        else:
            ty = "levels"

        for entry, attrs in list(parsed.get("sensor", {}).items()):
            if attrs["_location_"].startswith("%s." % location):
                attrs[ty] = (threshold, threshold)

    # Explanation from ELM2-MIB:
    # Empty string -> default, that means value in mV.
    # Universal: {[factor]}[unit]=$mV*[multiplicator]/[divisor]+[offset]
    # [multiplicator], [divisor], [offset] must be integers
    # Example: {0.1}%=$mV*20/100-100
    # default: {1}mV=$mV*1/1+0"
    # From the walk we get an ascii coded list separated by null bytes.
    # Results in: "=#\xb0C0.02-30.0" where
    # \xb0C => Temperature
    # 0.02  => 2/100 [multiplicator]/[divisor]
    # -30.0          [offset]
    # Notice, may also "=#\xb0C0.0230.0"
    for oidend, equation_bin in string_table[6]:
        equation = []
        part = []
        for entry in equation_bin:
            if entry:
                part.append(entry)
            elif part:
                equation.append("".join(map(chr, part)))
                part = []

        if not equation:
            continue

        if equation[0].endswith("#\xb0C"):
            sensor_ty = "sensor_temp"
        elif equation[0].endswith("#%RF"):
            sensor_ty = "sensor_humid"
        else:
            sensor_ty = "sensor_volt"

        equation = equation[1:]
        if len(equation) == 2:
            m, a = map(float, equation)
        else:
            m, a = 1.0, 0.0

        def scale_f(x, m=m, a=a):
            return float(x) * m + a

        location = str(chr(int(oidend.split(".", 1)[0])))
        for sensor, attrs in parsed.get("sensor", {}).items():
            if attrs["_location_"].endswith(".%s" % location):
                parsed.setdefault(sensor_ty, {})
                parsed[sensor_ty].setdefault(
                    sensor,
                    {
                        "value": scale_f(attrs["value"]),
                        "levels": list(map(scale_f, attrs["levels"])),
                        "levels_lower": list(map(scale_f, attrs["levels_lower"])),
                    },
                )
                break

    # Cleanup
    if "sensor" in parsed:
        del parsed["sensor"]

    return parsed


#   .--component-----------------------------------------------------------.
#   |                                                         _            |
#   |         ___ ___  _ __ ___  _ __   ___  _ __   ___ _ __ | |_          |
#   |        / __/ _ \| '_ ` _ \| '_ \ / _ \| '_ \ / _ \ '_ \| __|         |
#   |       | (_| (_) | | | | | | |_) | (_) | | | |  __/ | | | |_          |
#   |        \___\___/|_| |_| |_| .__/ \___/|_| |_|\___|_| |_|\__|         |
#   |                           |_|                                        |
#   +----------------------------------------------------------------------+
#   |                              main check                              |
#   '----------------------------------------------------------------------'


def discover_emka_modules(parsed):
    for entry, attrs in parsed["basic_components"].items():
        if attrs["activation"] != "i":
            yield entry, None


def check_emka_modules(item, params, parsed):
    map_activation_states = {
        "-": (0, "vacant"),
        "?": (0, "detect modus"),
        "x": (0, "excluded"),
        "e": (2, "error"),
        "c": (2, "collision detected"),
        "w": (1, "wait for dynamic address"),
        "P": (1, "polling"),
        "i": (0, "inactive"),
        "t": (2, "timeout"),
        "T": (2, "timeout alarm"),
        "A": (2, "alarm active"),
        "L": (0, "alarm latched"),
        "#": (0, "OK"),
    }

    if item in parsed["basic_components"]:
        attrs = parsed["basic_components"][item]
        state, state_readable = map_activation_states[attrs["activation"]]
        return state, "Activation status: {}, Type: {}".format(state_readable, attrs["type"])
    return None


check_info["emka_modules"] = LegacyCheckDefinition(
    name="emka_modules",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "emka"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13595"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.13595.2.1.3.3.1",
            oids=[OIDEnd(), "3", "4", "5", "7"],
        ),
        *(
            SNMPTree(
                base=f".1.3.6.1.4.1.13595.2.2.{table}.1",
                oids=[
                    "3",  # ELM2-MIB::coHandleModuleLink
                    "4",  # ELM2-MIB::co*[Status/Value]
                    "15",  # ELM2-MIB::coSensorMode
                ],
            )
            for table in _TABLES
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13595.2.2.3.1",
            oids=[OIDEnd(), "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13595.2.2.3.1",
            oids=[OIDEnd(), OIDBytes("18")],
        ),
    ],
    parse_function=parse_emka_modules,
    service_name="Module %s",
    discovery_function=discover_emka_modules,
    check_function=check_emka_modules,
)

# .
#   .--alarm---------------------------------------------------------------.
#   |                          _                                           |
#   |                     __ _| | __ _ _ __ _ __ ___                       |
#   |                    / _` | |/ _` | '__| '_ ` _ \                      |
#   |                   | (_| | | (_| | |  | | | | | |                     |
#   |                    \__,_|_|\__,_|_|  |_| |_| |_|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_emka_modules_alarm(parsed):
    for entry, attrs in parsed.get("alarm", {}).items():
        if attrs["value"] != "2":
            yield entry, None


def check_emka_modules_alarm(item, params, parsed):
    map_states = {
        "1": (3, "unknown"),
        "2": (0, "inactive"),
        "3": (2, "active"),
        "4": (0, "latched"),
    }

    if item in parsed.get("alarm", {}):
        state, state_readable = map_states[parsed["alarm"][item]["value"]]
        return state, "Status: %s" % state_readable
    return None


check_info["emka_modules.alarm"] = LegacyCheckDefinition(
    name="emka_modules_alarm",
    service_name="Alarm %s",
    sections=["emka_modules"],
    discovery_function=discover_emka_modules_alarm,
    check_function=check_emka_modules_alarm,
)

# .
#   .--handle--------------------------------------------------------------.
#   |                   _                     _ _                          |
#   |                  | |__   __ _ _ __   __| | | ___                     |
#   |                  | '_ \ / _` | '_ \ / _` | |/ _ \                    |
#   |                  | | | | (_| | | | | (_| | |  __/                    |
#   |                  |_| |_|\__,_|_| |_|\__,_|_|\___|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_emka_modules_handle(parsed):
    for entry, spec in parsed.get("handle", {}).items():
        if "value" in spec:
            yield entry, None


def check_emka_modules_handle(item, params, parsed):
    map_states = {
        "1": (0, "closed"),
        "2": (1, "opened"),
        "3": (3, "unlocked"),
        "4": (3, "delay"),
        "5": (2, "open time ex"),
    }

    if item in parsed.get("handle", {}):
        state, state_readable = map_states[parsed["handle"][item]["value"]]
        return state, "Status: %s" % state_readable
    return None


check_info["emka_modules.handle"] = LegacyCheckDefinition(
    name="emka_modules_handle",
    service_name="Handle %s",
    sections=["emka_modules"],
    discovery_function=discover_emka_modules_handle,
    check_function=check_emka_modules_handle,
)

# .
#   .--voltage-------------------------------------------------------------.
#   |                             _ _                                      |
#   |                 __   _____ | | |_ __ _  __ _  ___                    |
#   |                 \ \ / / _ \| | __/ _` |/ _` |/ _ \                   |
#   |                  \ V / (_) | | || (_| | (_| |  __/                   |
#   |                   \_/ \___/|_|\__\__,_|\__, |\___|                   |
#   |                                        |___/                         |
#   '----------------------------------------------------------------------'


def discover_emka_modules_sensor_volt(parsed):
    for entry in parsed.get("sensor_volt", {}):
        yield entry, {}


def check_emka_modules_sensor_volt(item, params, parsed):
    if item in parsed.get("sensor_volt", {}):
        attrs = parsed["sensor_volt"][item]
        value = attrs["value"] / 1000.0
        return check_elphase(item, params, {item: {"voltage": value}})
    return None


check_info["emka_modules.sensor_volt"] = LegacyCheckDefinition(
    name="emka_modules_sensor_volt",
    service_name="Phase %s",
    sections=["emka_modules"],
    discovery_function=discover_emka_modules_sensor_volt,
    check_function=check_emka_modules_sensor_volt,
    check_ruleset_name="el_inphase",
)

# .
#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def discover_emka_modules_sensor_temp(parsed):
    for entry in parsed.get("sensor_temp", {}):
        yield entry, {}


def check_emka_modules_sensor_temp(item, params, parsed):
    if item in parsed.get("sensor_temp", {}):
        attrs = parsed["sensor_temp"][item]
        value = attrs["value"]
        return check_temperature(
            value,
            params,
            "emka_modules_sensor_temp.%s" % item,
            dev_levels=attrs["levels"],
            dev_levels_lower=attrs["levels_lower"],
        )
    return None


check_info["emka_modules.sensor_temp"] = LegacyCheckDefinition(
    name="emka_modules_sensor_temp",
    service_name="Temperature %s",
    sections=["emka_modules"],
    discovery_function=discover_emka_modules_sensor_temp,
    check_function=check_emka_modules_sensor_temp,
    check_ruleset_name="temperature",
)

# .
#   .--humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def discover_emka_modules_sensor_humid(parsed):
    for entry in parsed.get("sensor_humid", {}):
        yield entry, {}


def check_emka_modules_sensor_humid(item, params, parsed):
    if item in parsed.get("sensor_humid", {}):
        attrs = parsed["sensor_humid"][item]
        value = attrs["value"]
        return check_humidity(value, params)
    return None


check_info["emka_modules.sensor_humid"] = LegacyCheckDefinition(
    name="emka_modules_sensor_humid",
    service_name="Humidity %s",
    sections=["emka_modules"],
    discovery_function=discover_emka_modules_sensor_humid,
    check_function=check_emka_modules_sensor_humid,
    check_ruleset_name="humidity",
)

# .
#   .--relay---------------------------------------------------------------.
#   |                                _                                     |
#   |                       _ __ ___| | __ _ _   _                         |
#   |                      | '__/ _ \ |/ _` | | | |                        |
#   |                      | | |  __/ | (_| | |_| |                        |
#   |                      |_|  \___|_|\__,_|\__, |                        |
#   |                                        |___/                         |
#   '----------------------------------------------------------------------'


def discover_emka_modules_relay(parsed):
    for entry, attrs in parsed.get("relay", {}).items():
        if attrs["value"] != "1":
            yield entry, None


def check_emka_modules_relay(item, params, parsed):
    map_states = {
        "1": (0, "off"),
        "2": (0, "on"),
    }

    if item in parsed.get("relay", {}):
        state, state_readable = map_states[parsed["relay"][item]["value"]]
        return state, "Status: %s" % state_readable
    return None


check_info["emka_modules.relay"] = LegacyCheckDefinition(
    name="emka_modules_relay",
    service_name="Relay %s",
    sections=["emka_modules"],
    discovery_function=discover_emka_modules_relay,
    check_function=check_emka_modules_relay,
)
