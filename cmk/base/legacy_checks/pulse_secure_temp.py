#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import cmk.base.plugins.agent_based.utils.pulse_secure as pulse_secure
from cmk.base.check_api import discover, LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


def parse_pulse_secure_temp(string_table: StringTable) -> Mapping[str, int]:
    return pulse_secure.parse_pulse_secure(string_table, "IVE")


# no get_parsed_item_data because the temperature can be exactly 0 for some devices, which would
# result in "UNKN - Item not found in SNMP data", because parsed[item] evaluates to False
def check_pulse_secure_temp(item, params, parsed):
    if not parsed:
        return None

    return check_temperature(parsed[item], params, "pulse_secure_ive_temperature")


check_info["pulse_secure_temp"] = LegacyCheckDefinition(
    detect=pulse_secure.DETECT_PULSE_SECURE,
    parse_function=parse_pulse_secure_temp,
    discovery_function=discover(),
    check_function=check_pulse_secure_temp,
    service_name="Pulse Secure %s Temperature",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12532",
        oids=["42"],
    ),
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (70.0, 75.0)},
)
