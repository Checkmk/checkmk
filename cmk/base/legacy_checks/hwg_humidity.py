#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.check_legacy_includes.hwg import parse_hwg

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree

check_info = {}

HWG_HUMIDITY_DEFAULTLEVELS = {"levels": (60.0, 70.0)}


def inventory_hwg_humidity(parsed):
    for index, attrs in parsed.items():
        if attrs.get("humidity"):
            yield index, {}


def check_hwg_humidity(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    status, infotext, perfdata = check_humidity(data["humidity"], params)
    infotext += " (Description: {}, Status: {})".format(data["descr"], data["dev_status_name"])
    yield status, infotext, perfdata


check_info["hwg_humidity"] = LegacyCheckDefinition(
    name="hwg_humidity",
    detect=contains(".1.3.6.1.2.1.1.1.0", "hwg"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21796.4.1.3.1",
        oids=["1", "2", "3", "4", "7"],
    ),
    parse_function=parse_hwg,
    service_name="Humidity %s",
    discovery_function=inventory_hwg_humidity,
    check_function=check_hwg_humidity,
    check_ruleset_name="humidity",
    check_default_parameters=HWG_HUMIDITY_DEFAULTLEVELS,
)

check_info["hwg_ste2.humidity"] = LegacyCheckDefinition(
    name="hwg_ste2_humidity",
    service_name="Humidity %s",
    sections=["hwg_ste2"],
    discovery_function=inventory_hwg_humidity,
    check_function=check_hwg_humidity,
    check_ruleset_name="humidity",
    check_default_parameters=HWG_HUMIDITY_DEFAULTLEVELS,
)
