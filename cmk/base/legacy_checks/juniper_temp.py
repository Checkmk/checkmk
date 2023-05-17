#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import any_of, LegacyCheckDefinition, startswith
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

# .1.3.6.1.4.1.2636.3.1.13.1.5.7.1.0.0 FPC: EX3300 48-Port @ 0/*/* --> SNMPv2-SMI::enterprises.2636.3.1.13.1.5.7.1.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.5.7.2.0.0 FPC: EX3300 48-Port @ 1/*/* --> SNMPv2-SMI::enterprises.2636.3.1.13.1.5.7.2.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.7.7.1.0.0 45 --> SNMPv2-SMI::enterprises.2636.3.1.13.1.7.7.1.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.7.7.2.0.0 43 --> SNMPv2-SMI::enterprises.2636.3.1.13.1.7.7.2.0.0

factory_settings["juniper_temp_default_levels"] = {
    "levels": (55.0, 60.0),  # Just an assumption based on observed real temperatures
}


def parse_juniper_temp(info):
    parsed = {}
    for description, reading_str in info:
        temperature = float(reading_str)
        if temperature > 0:
            description = description.replace(":", "").replace("/*", "").replace("@ ", "").strip()
            parsed[description] = temperature
    return parsed


def inventory_juniper_temp(parsed):
    return [(description, {}) for description in parsed]


def check_juniper_temp(item, params, parsed):
    if item in parsed:
        return check_temperature(parsed[item], params, "juniper_temp_%s" % item)
    return None


check_info["juniper_temp"] = LegacyCheckDefinition(
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2636.1.1.1.2"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2636.1.1.1.4"),
    ),
    parse_function=parse_juniper_temp,
    discovery_function=inventory_juniper_temp,
    check_function=check_juniper_temp,
    service_name="Temperature %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2636.3.1.13.1",
        oids=["5.7", "7.7"],
    ),
    check_ruleset_name="temperature",
    default_levels_variable="juniper_temp_default_levels",
    check_default_parameters={
        "levels": (55.0, 60.0),  # Just an assumption based on observed real temperatures
    },
)
