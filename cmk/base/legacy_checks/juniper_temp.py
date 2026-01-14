#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, SNMPTree, startswith
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# .1.3.6.1.4.1.2636.3.1.13.1.5.7.1.0.0 FPC: EX3300 48-Port @ 0/*/* --> SNMPv2-SMI::enterprises.2636.3.1.13.1.5.7.1.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.5.7.2.0.0 FPC: EX3300 48-Port @ 1/*/* --> SNMPv2-SMI::enterprises.2636.3.1.13.1.5.7.2.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.7.7.1.0.0 45 --> SNMPv2-SMI::enterprises.2636.3.1.13.1.7.7.1.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.7.7.2.0.0 43 --> SNMPv2-SMI::enterprises.2636.3.1.13.1.7.7.2.0.0


def parse_juniper_temp(string_table):
    parsed = {}
    for description, reading_str in string_table:
        temperature = float(reading_str)
        if temperature > 0:
            description = description.replace(":", "").replace("/*", "").replace("@ ", "").strip()
            parsed[description] = temperature
    return parsed


def discover_juniper_temp(parsed):
    return [(description, {}) for description in parsed]


def check_juniper_temp(item, params, parsed):
    if item in parsed:
        return check_temperature(parsed[item], params, "juniper_temp_%s" % item)
    return None


check_info["juniper_temp"] = LegacyCheckDefinition(
    name="juniper_temp",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2636.1.1.1.2"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2636.1.1.1.4"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2636.3.1.13.1",
        oids=["5.7", "7.7"],
    ),
    parse_function=parse_juniper_temp,
    service_name="Temperature %s",
    discovery_function=discover_juniper_temp,
    check_function=check_juniper_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (55.0, 60.0),  # Just an assumption based on observed real temperatures
    },
)
