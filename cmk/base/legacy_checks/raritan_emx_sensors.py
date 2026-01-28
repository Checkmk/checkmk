#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

#   .--binary--------------------------------------------------------------.
#   |                   _     _                                            |
#   |                  | |__ (_)_ __   __ _ _ __ _   _                     |
#   |                  | '_ \| | '_ \ / _` | '__| | | |                    |
#   |                  | |_) | | | | | (_| | |  | |_| |                    |
#   |                  |_.__/|_|_| |_|\__,_|_|   \__, |                    |
#   |                                            |___/                     |
#   +----------------------------------------------------------------------+
#   |                             main check                               |
#   '----------------------------------------------------------------------'
from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, OIDEnd, SNMPTree
from cmk.base.check_legacy_includes.raritan import (
    check_raritan_sensors,
    check_raritan_sensors_binary,
    check_raritan_sensors_temp,
    inventory_raritan_sensors,
    inventory_raritan_sensors_temp,
    parse_raritan_sensors,
)

check_info = {}


def discover_raritan_emx_sensors(
    parsed: Mapping[str, Mapping[str, Any]],
) -> Iterable[tuple[str, None]]:
    return inventory_raritan_sensors(parsed, "binary" or "")


check_info["raritan_emx_sensors"] = LegacyCheckDefinition(
    name="raritan_emx_sensors",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.8"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.8",
        oids=[
            "2.1.1.1.1",
            OIDEnd(),
            "1.2.1.1.5",
            "1.2.1.1.2",
            "2.1.1.1.2",
            "1.2.1.1.11",
            "1.2.1.1.12",
            "2.1.1.1.3",
            "1.2.1.1.20",
            "1.2.1.1.21",
            "1.2.1.1.22",
            "1.2.1.1.23",
        ],
    ),
    parse_function=parse_raritan_sensors,
    service_name="Contact %s",
    discovery_function=discover_raritan_emx_sensors,
    check_function=check_raritan_sensors_binary,
)


def discover_raritan_emx_sensors_temp(
    parsed: Mapping[str, Mapping[str, Any]],
) -> Iterable[tuple[str, Mapping[str, Any]]]:
    return inventory_raritan_sensors_temp(parsed, "temp")


# .
#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+

check_info["raritan_emx_sensors.temp"] = LegacyCheckDefinition(
    name="raritan_emx_sensors_temp",
    service_name="Temperature %s",
    sections=["raritan_emx_sensors"],
    discovery_function=discover_raritan_emx_sensors_temp,
    check_function=check_raritan_sensors_temp,
    check_ruleset_name="temperature",
)


def discover_raritan_emx_sensors_airflow(
    parsed: Mapping[str, Mapping[str, Any]],
) -> Iterable[tuple[str, None]]:
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

check_info["raritan_emx_sensors.airflow"] = LegacyCheckDefinition(
    name="raritan_emx_sensors_airflow",
    service_name="Air flow %s",
    sections=["raritan_emx_sensors"],
    discovery_function=discover_raritan_emx_sensors_airflow,
    check_function=check_raritan_sensors,
)


def discover_raritan_emx_sensors_humidity(
    parsed: Mapping[str, Mapping[str, Any]],
) -> Iterable[tuple[str, None]]:
    return inventory_raritan_sensors(parsed, "humidity")


# .
#   .--humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+

check_info["raritan_emx_sensors.humidity"] = LegacyCheckDefinition(
    name="raritan_emx_sensors_humidity",
    service_name="Humidity %s",
    sections=["raritan_emx_sensors"],
    discovery_function=discover_raritan_emx_sensors_humidity,
    check_function=check_raritan_sensors,
)


def discover_raritan_emx_sensors_pressure(
    parsed: Mapping[str, Mapping[str, Any]],
) -> Iterable[tuple[str, None]]:
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

check_info["raritan_emx_sensors.pressure"] = LegacyCheckDefinition(
    name="raritan_emx_sensors_pressure",
    service_name="Pressure %s",
    sections=["raritan_emx_sensors"],
    discovery_function=discover_raritan_emx_sensors_pressure,
    check_function=check_raritan_sensors,
)
