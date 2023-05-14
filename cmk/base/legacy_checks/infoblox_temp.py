#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.utils.infoblox import DETECT_INFOBLOX

# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.39 1 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.cpu1-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.40 5 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.cpu2-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.41 1 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.sys-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.39 CPU_TEMP: +36.00 C --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.cpu1-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.40 No temperature information available. --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.cpu2-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.41 SYS_TEMP: +34.00 C --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.sys-temp

# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.39 5 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.cpu1-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.40 5 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.cpu2-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.41 5 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.sys-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.39 --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.cpu1-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.40 --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.cpu2-temp
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.41 --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.sys-temp

# Suggested by customer
factory_settings["infoblox_temp_default_levels"] = {
    "levels": (40.0, 50.0),
}


def parse_infoblox_temp(info):
    map_states = {
        "1": (0, "working"),
        "2": (1, "warning"),
        "3": (2, "failed"),
        "4": (1, "inactive"),
        "5": (3, "unknown"),
    }

    parsed = {}
    # Just for a better handling
    for index, state, descr in list(zip(["", "1", "2", ""], info[0][0], info[1][0]))[1:]:
        if ":" not in descr:
            continue

        name, val_str = descr.split(":", 1)
        r_val, unit = val_str.split()
        val = float(r_val)

        what_name = "%s %s" % (name, index)
        parsed.setdefault(
            what_name.strip(),
            {
                "state": map_states[state],
                "reading": val,
                "unit": unit.lower(),
            },
        )

    return parsed


def inventory_infoblox_temp(parsed):
    yield from ((name, {}) for name in parsed)


def check_infoblox_temp(item, params, parsed):
    if sensor := parsed.get(item):
        return None

    devstate, devstatename = sensor["state"]
    return check_temperature(
        sensor["reading"],
        params,
        "infoblox_cpu_temp_%s" % item,
        dev_status=devstate,
        dev_status_name=devstatename,
        dev_unit=sensor["unit"],
    )


check_info["infoblox_temp"] = LegacyCheckDefinition(
    detect=DETECT_INFOBLOX,
    parse_function=parse_infoblox_temp,
    discovery_function=inventory_infoblox_temp,
    check_function=check_infoblox_temp,
    service_name="Temperature %s",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2",
            oids=[OIDEnd(), "39", "40", "41"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3",
            oids=[OIDEnd(), "39", "40", "41"],
        ),
    ],
    check_ruleset_name="temperature",
    default_levels_variable="infoblox_temp_default_levels",
)
