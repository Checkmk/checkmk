#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree
from cmk.base.check_legacy_includes.hwg import parse_hwg
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

HWG_TEMP_DEFAULTLEVELS = {"levels": (30.0, 35.0)}

READABLE_STATES = {
    "invalid": 3,
    "normal": 0,
    "out of range low": 2,
    "out of range high": 2,
    "alarm low": 2,
    "alarm high": 2,
}


def discover_hwg_temp(parsed):
    for index, attrs in parsed.items():
        if attrs.get("temperature") and attrs["dev_status_name"] not in ["invalid", ""]:
            yield index, {}


def check_hwg_temp(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    state = READABLE_STATES.get(data["dev_status_name"], 3)
    state_readable = data["dev_status_name"]
    temp = data["temperature"]
    if temp is None:
        yield state, "Status: %s" % state_readable
        return

    state, infotext, perfdata = check_temperature(
        temp,
        params,
        "hwg_temp_%s" % item,
        dev_unit=data["dev_unit"],
        dev_status=state,
        dev_status_name=state_readable,
    )

    infotext += " (Description: {}, Status: {})".format(data["descr"], data["dev_status_name"])
    yield state, "%s" % infotext, perfdata


check_info["hwg_temp"] = LegacyCheckDefinition(
    name="hwg_temp",
    detect=contains(".1.3.6.1.2.1.1.1.0", "hwg"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21796.4.1.3.1",
        oids=["1", "2", "3", "4", "7"],
    ),
    parse_function=parse_hwg,
    service_name="Temperature %s",
    discovery_function=discover_hwg_temp,
    check_function=check_hwg_temp,
    check_ruleset_name="temperature",
    check_default_parameters=HWG_TEMP_DEFAULTLEVELS,
)

check_info["hwg_ste2"] = LegacyCheckDefinition(
    name="hwg_ste2",
    detect=contains(".1.3.6.1.2.1.1.1.0", "STE2"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21796.4.9.3.1",
        oids=["1", "2", "3", "4", "7"],
    ),
    parse_function=parse_hwg,
    service_name="Temperature %s",
    discovery_function=discover_hwg_temp,
    check_function=check_hwg_temp,
    check_ruleset_name="temperature",
    check_default_parameters=HWG_TEMP_DEFAULTLEVELS,
)
