#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.didactum import (
    inventory_didactum_sensors,
    parse_didactum_sensors,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.didactum import DETECT_DIDACTUM


def inventory_didactum_sensors_outlet_relay(parsed):
    return inventory_didactum_sensors(parsed, "relay")


def check_didactum_sensors_outlet_relay(item, params, parsed):
    if item in parsed.get("relay", {}):
        data = parsed["relay"][item]
        return data["state"], "Status: %s" % data["state_readable"]
    return None


check_info["didactum_sensors_outlet"] = LegacyCheckDefinition(
    detect=DETECT_DIDACTUM,
    parse_function=parse_didactum_sensors,
    discovery_function=inventory_didactum_sensors_outlet_relay,
    check_function=check_didactum_sensors_outlet_relay,
    service_name="Relay %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.46501.5.3.1",
        oids=["4", "5", "6", "7"],
    ),
)
