#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.fireeye import check_fireeye_states
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.fireeye.lib import DETECT

check_info = {}

# .1.3.6.1.4.1.25597.11.1.1.4.0 32 --> FE-FIREEYE-MIB::feTemperatureValue.0
# .1.3.6.1.4.1.25597.11.1.1.5.0 Good --> FE-FIREEYE-MIB::feTemperatureStatus.0
# .1.3.6.1.4.1.25597.11.1.1.6.0 1 --> FE-FIREEYE-MIB::feTemperatureIsHealthy.0


def discover_fireeye_temp(info):
    if info:
        return [("system", {})]
    return []


def check_fireeye_temp(item, params, info):
    reading_str, status, health = info[0]
    dev_status = 0
    dev_status_name = ""
    for text, (state, state_readable) in check_fireeye_states(
        [(status, "Status"), (health, "Health")]
    ).items():
        dev_status = max(dev_status, state)
        dev_status_name += f"{text}: {state_readable}"

    yield check_temperature(
        float(reading_str),
        params,
        "fireeye_temp_system",
        dev_status=dev_status,
        dev_status_name=dev_status_name,
    )


def parse_fireeye_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["fireeye_temp"] = LegacyCheckDefinition(
    name="fireeye_temp",
    parse_function=parse_fireeye_temp,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.1.1",
        oids=["4", "5", "6"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_fireeye_temp,
    check_function=check_fireeye_temp,
    check_ruleset_name="temperature",
)
