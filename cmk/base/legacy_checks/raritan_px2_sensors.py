#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.check_legacy_includes.raritan import (
    check_raritan_sensors,
    check_raritan_sensors_temp,
    inventory_raritan_sensors,
    inventory_raritan_sensors_temp,
    parse_raritan_sensors,
)

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyCheckResult
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.plugins.lib.raritan import DETECT_RARITAN

check_info = {}


def discover_raritan_px2_sensors(parsed):
    return inventory_raritan_sensors_temp(parsed, "temp")


#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                             main check                               |
#   '----------------------------------------------------------------------'


check_info["raritan_px2_sensors"] = LegacyCheckDefinition(
    name="raritan_px2_sensors",
    detect=DETECT_RARITAN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6",
        oids=[
            "5.5.3.1.2.1",
            OIDEnd(),
            "3.6.3.1.5.1",
            "3.6.3.1.2.1",
            "5.5.3.1.3.1",
            "3.6.3.1.16.1",
            "3.6.3.1.17.1",
            "5.5.3.1.4.1",
            "3.6.3.1.31.1",
            "3.6.3.1.32.1",
            "3.6.3.1.33.1",
            "3.6.3.1.34.1",
        ],
    ),
    parse_function=parse_raritan_sensors,
    service_name="Temperature %s",
    discovery_function=discover_raritan_px2_sensors,
    check_function=check_raritan_sensors_temp,
    check_ruleset_name="temperature",
)


def discover_raritan_px2_sensors_airflow(parsed):
    return inventory_raritan_sensors(parsed, "airflow")


# .
#   .--airflow-------------------------------------------------------------.
#   |                        _       __ _                                  |
#   |                   __ _(_)_ __ / _| | _____      __                   |
#   |                  / _` | | '__| |_| |/ _ \ \ /\ / /                   |
#   |                 | (_| | | |  |  _| | (_) \ V  V /                    |
#   |                  \__,_|_|_|  |_| |_|\___/ \_/\_/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+

check_info["raritan_px2_sensors.airflow"] = LegacyCheckDefinition(
    name="raritan_px2_sensors_airflow",
    service_name="Air flow %s",
    sections=["raritan_px2_sensors"],
    discovery_function=discover_raritan_px2_sensors_airflow,
    check_function=check_raritan_sensors,
)


def discover_raritan_px2_sensors_humidity(parsed):
    return inventory_raritan_sensors(parsed, "humidity")


def check_raritan_sensors_humidity(
    item: str,
    params: Mapping[str, tuple[float, float]],
    section: Mapping[str, Mapping[str, Any]],
) -> LegacyCheckResult:
    if (sensor := section.get(item)) is None:
        return None

    humidity_value, crit_lower, warn_lower, crit, warn = sensor["sensor_data"]

    if "levels" in params:
        warn, crit = params["levels"]
    if "levels_lower" in params:
        warn_lower, crit_lower = params["levels_lower"]

    yield check_humidity(
        humidity=humidity_value,
        params={
            "levels": (warn, crit),
            "levels_lower": (warn_lower, crit_lower),
        },
    )

    state, state_readable = sensor["state"]
    yield state, f"Device status: {state_readable}"


# .
#   .--humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+

check_info["raritan_px2_sensors.humidity"] = LegacyCheckDefinition(
    name="raritan_px2_sensors_humidity",
    service_name="Humidity %s",
    sections=["raritan_px2_sensors"],
    discovery_function=discover_raritan_px2_sensors_humidity,
    check_function=check_raritan_sensors_humidity,
    check_ruleset_name="humidity",
)


def discover_raritan_px2_sensors_pressure(parsed):
    return inventory_raritan_sensors(parsed, "pressure")


# .
#   .--pressure------------------------------------------------------------.
#   |                                                                      |
#   |               _ __  _ __ ___  ___ ___ _   _ _ __ ___                 |
#   |              | '_ \| '__/ _ \/ __/ __| | | | '__/ _ \                |
#   |              | |_) | | |  __/\__ \__ \ |_| | | |  __/                |
#   |              | .__/|_|  \___||___/___/\__,_|_|  \___|                |
#   |              |_|                                                     |
#   +----------------------------------------------------------------------+

check_info["raritan_px2_sensors.pressure"] = LegacyCheckDefinition(
    name="raritan_px2_sensors_pressure",
    service_name="Pressure %s",
    sections=["raritan_px2_sensors"],
    discovery_function=discover_raritan_px2_sensors_pressure,
    check_function=check_raritan_sensors,
)
