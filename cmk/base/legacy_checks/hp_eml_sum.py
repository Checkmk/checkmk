#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, SNMPTree, StringTable

check_info = {}

hp_eml_sum_map = {
    # snmp_value: (nagios_status, txt)
    "1": (3, "unknown"),
    "2": (0, "unused"),
    "3": (0, "ok"),
    "4": (1, "warning"),
    "5": (2, "critical"),
    "6": (2, "nonrecoverable"),
}


def discover_hp_eml_sum(info):
    if info and info[0]:
        return [(None, None)]
    return []


def check_hp_eml_sum(_no_item, _no_param, info):
    if not info or not info[0]:
        return (3, "Summary status information missing")

    op_status, manufacturer, model, serial, version = info[0]
    status, status_txt = hp_eml_sum_map.get(op_status, (3, "unhandled op_status (%s)" % op_status))

    return (
        status,
        'Summary State is "%s", Manufacturer: %s, '
        "Model: %s, Serial: %s, Version: %s" % (status_txt, manufacturer, model, serial, version),
    )


def parse_hp_eml_sum(string_table: StringTable) -> StringTable:
    return string_table


check_info["hp_eml_sum"] = LegacyCheckDefinition(
    name="hp_eml_sum",
    parse_function=parse_hp_eml_sum,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11.10.2.1.3.20"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.36.1.1.5.1.1",
        oids=["3", "7", "9", "10", "11"],
    ),
    service_name="Summary Status",
    discovery_function=discover_hp_eml_sum,
    check_function=check_hp_eml_sum,
)
