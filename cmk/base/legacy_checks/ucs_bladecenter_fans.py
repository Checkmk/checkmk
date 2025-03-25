#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.temperature import check_temperature_list, CheckTempKwargs

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.plugins.lib import ucs_bladecenter

check_info = {}

# <<ucs_bladecenter_fans:sep(9)>>>
# equipmentNetworkElementFanStats Dn sys/switch-A/fan-module-1-1/fan-1/stats      SpeedAvg 8542
# equipmentFanModuleStats Dn sys/chassis-2/fan-module-1-1/stats   AmbientTemp 29.000000
# equipmentFan    Dn sys/chassis-1/fan-module-1-1/fan-1   Model N20-FAN5  OperState operable
# equipmentFanStats       Dn sys/chassis-2/fan-module-1-1/fan-1/stats     SpeedAvg 3652


def parse_ucs_bladecenter_fans(string_table):
    data = ucs_bladecenter.generic_parse(string_table)
    fans: dict[str, dict] = {}

    def get_item_name(key):
        tokens = key.split("/")
        tokens[1] = tokens[1].replace("fan-module-", "Module ").replace("-", ".")
        tokens = [x[0].upper() + x[1:] for x in tokens]
        if len(tokens) > 2:
            tokens[2] = tokens[2].replace("fan-", ".")
        return " ".join(tokens).replace("-", " ")

    for component, key_low, key_high in [
        ("equipmentNetworkElementFanStats", 4, -6),
        ("equipmentFanModuleStats", 4, -6),
        ("equipmentFan", 4, 100),
        ("equipmentFanStats", 4, -6),
    ]:
        for key, values in data.get(component, {}).items():
            fan = key[key_low:key_high]
            del values["Dn"]
            name = get_item_name(fan)
            fans.setdefault(name, {}).update(values)

    return fans


#   .--Fans----------------------------------------------------------------.
#   |                         _____                                        |
#   |                        |  ___|_ _ _ __  ___                          |
#   |                        | |_ / _` | '_ \/ __|                         |
#   |                        |  _| (_| | | | \__ \                         |
#   |                        |_|  \__,_|_| |_|___/                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_ucs_bladecenter_fans(parsed):
    for key, values in parsed.items():
        if "SpeedAvg" in values:
            yield " ".join(key.split()[:2]), None


def check_ucs_bladecenter_fans(item, _no_params, parsed):
    my_fans = {}
    for key, values in parsed.items():
        if key.startswith(item) and "OperState" in values:
            my_fans[key] = values

    if not my_fans:
        yield 3, "Fan statistics not available"
        return

    yield 0, "%d Fans" % len(my_fans)
    for key, fan in sorted(my_fans.items()):
        if fan["OperState"] != "operable":
            yield (
                2,
                "Fan {} {}: average speed {} RPM".format(
                    key.split()[-1][2:],
                    fan["OperState"],
                    fan.get("SpeedAvg"),
                ),
            )


check_info["ucs_bladecenter_fans"] = LegacyCheckDefinition(
    name="ucs_bladecenter_fans",
    parse_function=parse_ucs_bladecenter_fans,
    service_name="Fans %s",
    discovery_function=inventory_ucs_bladecenter_fans,
    check_function=check_ucs_bladecenter_fans,
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


# Fans are grouped per module, usually 8 components
def inventory_ucs_bladecenter_fans_temp(parsed):
    for key, values in parsed.items():
        if "AmbientTemp" in values:
            yield "Ambient %s FAN" % " ".join(key.split()[:2]), {}


def check_ucs_bladecenter_fans_temp(item, params, parsed):
    sensor_item = item[8:-4]  # drop "Ambient " and " FAN"
    sensor_list: list[tuple[str, int | float, CheckTempKwargs]] = []
    for key, values in parsed.items():
        if key.startswith(sensor_item) and "AmbientTemp" in values:
            loc = key.split()[-1].split(".")
            sensor_list.append(
                (
                    f"Module {loc[0]} Fan {loc[1]}",
                    float(values.get("AmbientTemp")),
                    {},
                )
            )
    yield from check_temperature_list(sensor_list, params)


check_info["ucs_bladecenter_fans.temp"] = LegacyCheckDefinition(
    name="ucs_bladecenter_fans_temp",
    service_name="Temperature %s",
    sections=["ucs_bladecenter_fans"],
    discovery_function=inventory_ucs_bladecenter_fans_temp,
    check_function=check_ucs_bladecenter_fans_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (40.0, 50.0),
    },
)
