#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    exists,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


def parse_fast_lta_headunit(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_fast_lta_headunit = SNMPSection(
    name="fast_lta_headunit",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        any_of(exists(".1.3.6.1.4.1.27417.2.1"), exists(".1.3.6.1.4.1.27417.2.1.0")),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.27417.2",
            oids=["1", "2", "5"],
        )
    ],
    parse_function=parse_fast_lta_headunit,
)


#   .--status--------------------------------------------------------------.
#   |                         _        _                                   |
#   |                     ___| |_ __ _| |_ _   _ ___                       |
#   |                    / __| __/ _` | __| | | / __|                      |
#   |                    \__ \ || (_| | |_| |_| \__ \                      |
#   |                    |___/\__\__,_|\__|\__,_|___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_fast_lta_headunit_status(section: Sequence[StringTable]) -> DiscoveryResult:
    if section[0]:
        yield Service()


def check_fast_lta_headunit_status(section: Sequence[StringTable]) -> CheckResult:
    try:
        head_unit_status, app_read_only_status = section[0][0][:2]
    except IndexError:
        return

    head_unit_status_map = {
        "-1": "workerDefect",
        "-2": "workerNotStarted",
        "2": "workerBooting",
        "3": "workerRfRRunning",
        "10": "appBooting",
        "20": "appNoCubes",
        "30": "appVirginCubes",
        "40": "appRfrPossible",
        "45": "appRfrMixedCubes",
        "50": "appRfrActive",
        "60": "appReady",
        "65": "appMixedCubes",
        "70": "appReadOnly",
        "75": "appEnterpriseCubes",
        "80": "appEnterpriseMixedCubes",
    }

    if head_unit_status == "60":
        state = State.OK
    elif head_unit_status == "70" and app_read_only_status == "0":
        # on Slave node appReadOnly is also an ok state
        state = State.OK
    else:
        state = State.CRIT

    if head_unit_status in head_unit_status_map:
        message = f"Head Unit status is {head_unit_status_map[head_unit_status]}."
    else:
        message = f"Head Unit status is {head_unit_status}."

    yield Result(state=state, summary=message)


check_plugin_fast_lta_headunit_status = CheckPlugin(
    name="fast_lta_headunit_status",
    service_name="Fast LTA Headunit Status",
    sections=["fast_lta_headunit"],
    discovery_function=discover_fast_lta_headunit_status,
    check_function=check_fast_lta_headunit_status,
)

# .
#   .--replication---------------------------------------------------------.
#   |                          _ _           _   _                         |
#   |           _ __ ___ _ __ | (_) ___ __ _| |_(_) ___  _ __              |
#   |          | '__/ _ \ '_ \| | |/ __/ _` | __| |/ _ \| '_ \             |
#   |          | | |  __/ |_) | | | (_| (_| | |_| | (_) | | | |            |
#   |          |_|  \___| .__/|_|_|\___\__,_|\__|_|\___/|_| |_|            |
#   |                   |_|                                                |
#   '----------------------------------------------------------------------'


def inventory_fast_lta_headunit_replication(section: Sequence[StringTable]) -> DiscoveryResult:
    if section[0]:
        yield Service()


def check_fast_lta_headunit_replication(section: Sequence[StringTable]) -> CheckResult:
    try:
        node_replication_mode, replication_status = section[0][0][1:3]
    except IndexError:
        return

    head_unit_replication_map = {
        "0": "Slave",
        "1": "Master",
        "255": "standalone",
    }

    if replication_status == "1":
        message = "Replication is running."
        state = State.OK
    else:
        message = "Replication is not running (!!)."
        state = State.CRIT

    if node_replication_mode in head_unit_replication_map:
        message += f" This node is {head_unit_replication_map[node_replication_mode]}."
    else:
        message += f" Replication mode of this node is {node_replication_mode}."

    yield Result(state=state, summary=message)


check_plugin_fast_lta_headunit_replication = CheckPlugin(
    name="fast_lta_headunit_replication",
    service_name="Fast LTA Replication",
    sections=["fast_lta_headunit"],
    discovery_function=inventory_fast_lta_headunit_replication,
    check_function=check_fast_lta_headunit_replication,
)

# .
