#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.raritan import (
    check_raritan_sensors,
    check_raritan_sensors_binary,
    check_raritan_sensors_temp,
    inventory_raritan_sensors,
    inventory_raritan_sensors_temp,
    parse_raritan_sensors,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import equals, OIDEnd, SNMPTree

check_info["raritan_emx_sensors"] = LegacyCheckDefinition(
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.8"),
    parse_function=parse_raritan_sensors,
    discovery_function=lambda parsed: inventory_raritan_sensors(parsed, "binary" or ""),
    check_function=check_raritan_sensors_binary,
    service_name="Contact %s",
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
)

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
    discovery_function=lambda parsed: inventory_raritan_sensors_temp(parsed, "temp"),
    check_function=check_raritan_sensors_temp,
    service_name="Temperature %s",
    check_ruleset_name="temperature",
)

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
    discovery_function=lambda parsed: inventory_raritan_sensors(parsed, "airflow"),
    check_function=check_raritan_sensors,
    service_name="Air flow %s",
)

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
    discovery_function=lambda parsed: inventory_raritan_sensors(parsed, "humidity"),
    check_function=check_raritan_sensors,
    service_name="Humidity %s",
)

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
    discovery_function=lambda parsed: inventory_raritan_sensors(parsed, "pressure"),
    check_function=check_raritan_sensors,
    service_name="Pressure %s",
)
