#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.didactum import (
    discover_didactum_sensors,
    parse_didactum_sensors,
)
from cmk.plugins.didactum.lib import DETECT_DIDACTUM

check_info = {}


def discover_didactum_sensors_outlet_relay(parsed):
    return discover_didactum_sensors(parsed, "relay")


def check_didactum_sensors_outlet_relay(item, params, parsed):
    if item in parsed.get("relay", {}):
        data = parsed["relay"][item]
        return data["state"], "Status: %s" % data["state_readable"]
    return None


check_info["didactum_sensors_outlet"] = LegacyCheckDefinition(
    name="didactum_sensors_outlet",
    detect=DETECT_DIDACTUM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.46501.5.3.1",
        oids=["4", "5", "6", "7"],
    ),
    parse_function=parse_didactum_sensors,
    service_name="Relay %s",
    discovery_function=discover_didactum_sensors_outlet_relay,
    check_function=check_didactum_sensors_outlet_relay,
)
