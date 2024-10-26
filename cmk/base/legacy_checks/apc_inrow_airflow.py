#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.apc import DETECT

check_info = {}


def inventory_apc_inrow_airflow(info):
    if info:
        yield None, {}


def check_apc_inrow_airflow(_no_item, params, info):
    # The MIB states that this value is given in hundredths of liters per second.
    # However, it appears that the device actually returns l/s, as the oom should
    # be closer to 1000 l/s. (cf. https://www.apc.com/salestools/DRON-AAAR53/DRON-AAAR53_R1_EN.pdf)
    try:
        flow = float(info[0][0])
    except Exception:
        return None

    state = 0
    message = ""

    warn, crit = params["level_low"]
    if flow < crit:
        state = 2
        message = "too low"
    elif flow < warn:
        state = 1
        message = "too low"

    warn, crit = params["level_high"]
    if flow >= crit:
        state = 2
        message = "too high"
    elif flow >= warn:
        state = 1
        message = "too high"

    perf = [("airflow", flow, warn, crit)]
    return state, f"Current: {flow:.0f} l/s {message}", perf


def parse_apc_inrow_airflow(string_table: StringTable) -> StringTable:
    return string_table


check_info["apc_inrow_airflow"] = LegacyCheckDefinition(
    name="apc_inrow_airflow",
    parse_function=parse_apc_inrow_airflow,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.13.3.2.2.2",
        oids=["5"],
    ),
    service_name="Airflow",
    discovery_function=inventory_apc_inrow_airflow,
    check_function=check_apc_inrow_airflow,
    check_ruleset_name="airflow",
    check_default_parameters={
        "level_low": (500.0, 200.0),
        "level_high": (1000.0, 1100.0),
    },
)
