#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.apc.lib_ats import DETECT


def inventory_apc_inrow_airflow(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_apc_inrow_airflow(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    # The MIB states that this value is given in hundredths of liters per second.
    # However, it appears that the device actually returns l/s, as the oom should
    # be closer to 1000 l/s. (cf. https://www.apc.com/salestools/DRON-AAAR53/DRON-AAAR53_R1_EN.pdf)
    try:
        flow = float(section[0][0])
    except Exception:
        return

    state = State.OK
    message = ""

    warn_low, crit_low = params["level_low"]
    if flow < crit_low:
        state = State.CRIT
        message = "too low"
    elif flow < warn_low:
        state = State.WARN
        message = "too low"

    warn_high, crit_high = params["level_high"]
    if flow >= crit_high:
        state = State.CRIT
        message = "too high"
    elif flow >= warn_high:
        state = State.WARN
        message = "too high"

    yield Result(state=state, summary=f"Current: {flow:.0f} l/s {message}")
    yield Metric("airflow", flow, levels=(warn_high, crit_high))


def parse_apc_inrow_airflow(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_apc_inrow_airflow = SimpleSNMPSection(
    name="apc_inrow_airflow",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.13.3.2.2.2",
        oids=["5"],
    ),
    parse_function=parse_apc_inrow_airflow,
)


check_plugin_apc_inrow_airflow = CheckPlugin(
    name="apc_inrow_airflow",
    service_name="Airflow",
    discovery_function=inventory_apc_inrow_airflow,
    check_function=check_apc_inrow_airflow,
    check_ruleset_name="airflow",
    check_default_parameters={
        "level_low": (500.0, 200.0),
        "level_high": (1000.0, 1100.0),
    },
)
