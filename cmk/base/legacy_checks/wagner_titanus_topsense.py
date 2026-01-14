#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from collections.abc import Sequence

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, equals, render, SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}


def parse_wagner_titanus_topsense(
    string_table: Sequence[StringTable],
) -> Sequence[StringTable] | None:
    return string_table if string_table[0] else None


check_info["wagner_titanus_topsense"] = LegacyCheckDefinition(
    name="wagner_titanus_topsense",
    parse_function=parse_wagner_titanus_topsense,
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.34187.21501"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.34187.74195"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.1",
            oids=["1", "3", "4", "5", "6"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34187.21501.1.1",
            oids=["1", "2", "3", "1000", "1001", "1002", "1003", "1004", "1005", "1006"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34187.21501.2.1",
            oids=[
                "245810000",
                "245820000",
                "245950000",
                "246090000",
                "245960000",
                "246100000",
                "245970000",
                "246110000",
                "24584008",
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34187.74195.1.1",
            oids=["1", "2", "3", "1000", "1001", "1002", "1003", "1004", "1005", "1006"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.34187.74195.2.1",
            oids=[
                "245790000",
                "245800000",
                "245940000",
                "246060000",
                "245950000",
                "246070000",
                "245960000",
                "246080000",
            ],
        ),
    ],
)


def parse_wagner_titanus_topsens(info):
    # not much of a parse function. simply retrieves the info blocks that apply for the
    # respective topsens model and returns only those
    res = [info[0], info[1] or info[3], info[2] or info[4]]
    return res


#   .--titanus info--------------------------------------------------------.
#   |         _   _ _                          _        __                 |
#   |        | |_(_) |_ __ _ _ __  _   _ ___  (_)_ __  / _| ___            |
#   |        | __| | __/ _` | '_ \| | | / __| | | '_ \| |_ / _ \           |
#   |        | |_| | || (_| | | | | |_| \__ \ | | | | |  _| (_) |          |
#   |         \__|_|\__\__,_|_| |_|\__,_|___/ |_|_| |_|_|  \___/           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_wagner_titanus_topsense_info(info):
    yield None, {}


def check_wagner_titanus_topsense_info(item, _no_params, info):
    parsed = parse_wagner_titanus_topsens(info)
    message = "System: " + parsed[0][0][0]
    message += ", Uptime: " + render.timespan(int(parsed[0][0][1]) // 100)
    message += ", System Name: " + parsed[0][0][3]
    message += ", System Contact: " + parsed[0][0][2]
    message += ", System Location: " + parsed[0][0][4]
    message += ", Company: " + parsed[1][0][0]
    message += ", Model: " + parsed[1][0][1]
    message += ", Revision: " + parsed[1][0][2]
    if len(info) > 8:
        ts_lsn_bus = parsed[2][0][8]
        if ts_lsn_bus == "0":
            ts_lsn_bus = "offline"
        elif ts_lsn_bus == "1":
            ts_lsn_bus = "online"
        else:
            ts_lsn_bus = "unknown"

        message += ", LSNi bus: " + ts_lsn_bus
    return 0, message


check_info["wagner_titanus_topsense.info"] = LegacyCheckDefinition(
    name="wagner_titanus_topsense_info",
    service_name="Topsense Info",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_info,
    check_function=check_wagner_titanus_topsense_info,
)

# .
#   .--overall status------------------------------------------------------.
#   |                               _ _       _        _                   |
#   |       _____   _____ _ __ __ _| | |  ___| |_ __ _| |_ _   _ ___       |
#   |      / _ \ \ / / _ \ '__/ _` | | | / __| __/ _` | __| | | / __|      |
#   |     | (_) \ V /  __/ | | (_| | | | \__ \ || (_| | |_| |_| \__ \      |
#   |      \___/ \_/ \___|_|  \__,_|_|_| |___/\__\__,_|\__|\__,_|___/      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_wagner_titanus_topsense_overall_status(info):
    yield None, {}


def check_wagner_titanus_topsense_overall_status(item, _no_params, info):
    parsed = parse_wagner_titanus_topsens(info)
    psw_failure = parsed[1][0][9]
    status = 3
    if psw_failure == "0":
        message = "Overall Status reports OK"
        status = 0
    else:
        message = "Overall Status reports a problem"
        status = 2
    return status, message


check_info["wagner_titanus_topsense.overall_status"] = LegacyCheckDefinition(
    name="wagner_titanus_topsense_overall_status",
    service_name="Overall Status",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_overall_status,
    check_function=check_wagner_titanus_topsense_overall_status,
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


def discover_wagner_titanus_topsense_alarm(info):
    yield "1", {}
    yield "2", {}


def check_wagner_titanus_topsense_alarm(item, _no_params, info):
    parsed = parse_wagner_titanus_topsens(info)
    if item == "1":
        main_alarm = parsed[1][0][3]
        pre_alarm = parsed[1][0][4]
        info_alarm = parsed[1][0][5]
    elif item == "2":
        main_alarm = parsed[1][0][6]
        pre_alarm = parsed[1][0][7]
        info_alarm = parsed[1][0][8]
    else:
        return 3, "Alarm Detector %s not found in SNMP" % item

    status = 0
    message = "No Alarm"
    if info_alarm != "0":
        message = "Info Alarm"
        status = 1
    if pre_alarm != "0":
        message = "Pre Alarm"
        status = 1
    if main_alarm != "0":
        message = "Main Alarm: Fire"
        status = 2

    return status, message


check_info["wagner_titanus_topsense.alarm"] = LegacyCheckDefinition(
    name="wagner_titanus_topsense_alarm",
    service_name="Alarm Detector %s",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_alarm,
    check_function=check_wagner_titanus_topsense_alarm,
)

# .
#   .--smoke percent-------------------------------------------------------.
#   |                      _                                        _      |
#   |  ___ _ __ ___   ___ | | _____   _ __   ___ _ __ ___ ___ _ __ | |_    |
#   | / __| '_ ` _ \ / _ \| |/ / _ \ | '_ \ / _ \ '__/ __/ _ \ '_ \| __|   |
#   | \__ \ | | | | | (_) |   <  __/ | |_) |  __/ | | (_|  __/ | | | |_    |
#   | |___/_| |_| |_|\___/|_|\_\___| | .__/ \___|_|  \___\___|_| |_|\__|   |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


def discover_wagner_titanus_topsense_smoke(info):
    yield "1", {}
    yield "2", {}


def check_wagner_titanus_topsense_smoke(item, _no_params, info):
    parsed = parse_wagner_titanus_topsens(info)
    if item == "1":
        smoke_perc = float(parsed[2][0][0])
    elif item == "2":
        smoke_perc = float(parsed[2][0][1])
    else:
        return 3, "Smoke Detector %s not found in SNMP" % item

    perfdata = [("smoke_perc", smoke_perc)]
    if smoke_perc > 5:
        status = 2
    elif smoke_perc > 3:
        status = 1
    else:
        status = 0

    return status, "%0.6f%% smoke detected" % smoke_perc, perfdata


check_info["wagner_titanus_topsense.smoke"] = LegacyCheckDefinition(
    name="wagner_titanus_topsense_smoke",
    service_name="Smoke Detector %s",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_smoke,
    check_function=check_wagner_titanus_topsense_smoke,
)

# .
#   .--chamber deviation---------------------------------------------------.
#   |         _                     _                     _                |
#   |     ___| |__   __ _ _ __ ___ | |__   ___ _ __    __| | _____   __    |
#   |    / __| '_ \ / _` | '_ ` _ \| '_ \ / _ \ '__|  / _` |/ _ \ \ / /    |
#   |   | (__| | | | (_| | | | | | | |_) |  __/ |    | (_| |  __/\ V /     |
#   |    \___|_| |_|\__,_|_| |_| |_|_.__/ \___|_|     \__,_|\___| \_/      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_wagner_titanus_topsense_chamber_deviation(info):
    yield "1", {}
    yield "2", {}


def check_wagner_titanus_topsense_chamber_deviation(item, _no_params, info):
    parsed = parse_wagner_titanus_topsens(info)
    if item == "1":
        chamber_deviation = float(parsed[2][0][2])
    elif item == "2":
        chamber_deviation = float(parsed[2][0][3])
    else:
        return 3, "Chamber Deviation Detector %s not found in SNMP" % item

    perfdata = [("chamber_deviation", chamber_deviation)]

    return 0, "%0.6f%% Chamber Deviation" % chamber_deviation, perfdata


check_info["wagner_titanus_topsense.chamber_deviation"] = LegacyCheckDefinition(
    name="wagner_titanus_topsense_chamber_deviation",
    service_name="Chamber Deviation Detector %s",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_chamber_deviation,
    check_function=check_wagner_titanus_topsense_chamber_deviation,
)

# .
#   .--air flow deviation--------------------------------------------------.
#   |              _         __ _                     _                    |
#   |         __ _(_)_ __   / _| | _____      __   __| | _____   __        |
#   |        / _` | | '__| | |_| |/ _ \ \ /\ / /  / _` |/ _ \ \ / /        |
#   |       | (_| | | |    |  _| | (_) \ V  V /  | (_| |  __/\ V /         |
#   |        \__,_|_|_|    |_| |_|\___/ \_/\_/    \__,_|\___| \_/          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_wagner_titanus_topsense_airflow_deviation(info):
    yield "1", {}
    yield "2", {}


def check_wagner_titanus_topsense_airflow_deviation(item, params, info):
    parsed = parse_wagner_titanus_topsens(info)
    if item == "1":
        airflow_deviation = float(parsed[2][0][4])
    elif item == "2":
        airflow_deviation = float(parsed[2][0][5])
    else:
        return

    yield check_levels(
        airflow_deviation,
        "airflow_deviation",
        params["levels_upper"] + params["levels_lower"],
        human_readable_func=lambda v: "%0.6f%%",
        infoname="Airflow deviation",
    )


check_info["wagner_titanus_topsense.airflow_deviation"] = LegacyCheckDefinition(
    name="wagner_titanus_topsense_airflow_deviation",
    service_name="Airflow Deviation Detector %s",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_airflow_deviation,
    check_function=check_wagner_titanus_topsense_airflow_deviation,
    check_ruleset_name="airflow_deviation",
    check_default_parameters={
        "levels_upper": (20.0, 20.0),
        "levels_lower": (-20.0, -20.0),
    },
)

# .
#   .--air temp------------------------------------------------------------.
#   |                     _        _                                       |
#   |                __ _(_)_ __  | |_ ___ _ __ ___  _ __                  |
#   |               / _` | | '__| | __/ _ \ '_ ` _ \| '_ \                 |
#   |              | (_| | | |    | ||  __/ | | | | | |_) |                |
#   |               \__,_|_|_|     \__\___|_| |_| |_| .__/                 |
#   |                                               |_|                    |
#   '----------------------------------------------------------------------'


def discover_wagner_titanus_topsense_temp(info):
    yield "Ambient 1", {}
    yield "Ambient 2", {}


def check_wagner_titanus_topsense_temp(item, params, info):
    parsed = parse_wagner_titanus_topsens(info)
    if not item.startswith("Ambient"):
        item = "Ambient %s" % item

    if item == "Ambient 1":
        temp = float(parsed[2][0][6])
    elif item == "Ambient 2":
        temp = float(parsed[2][0][7])
    else:
        return None

    return check_temperature(temp, params, "wagner_titanus_topsense_%s" % item)


check_info["wagner_titanus_topsense.temp"] = LegacyCheckDefinition(
    name="wagner_titanus_topsense_temp",
    service_name="Temperature %s",
    sections=["wagner_titanus_topsense"],
    discovery_function=discover_wagner_titanus_topsense_temp,
    check_function=check_wagner_titanus_topsense_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (30.0, 35.0),
    },
)

# .
