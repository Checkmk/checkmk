#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from typing import TypedDict

from cmk.agent_based.v2 import (
    any_of,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    LevelsT,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


class CheckParamT(TypedDict):
    levels: LevelsT


class Section(TypedDict):
    operation_status: str
    connected_clients: int
    links: int
    successful_connections: int
    failed_connections: int
    expiration_date: str


def parse_safenet_ntls(string_table: StringTable) -> Section | None:
    return (
        Section(
            operation_status=string_table[0][0],
            connected_clients=int(string_table[0][1]),
            links=int(string_table[0][2]),
            successful_connections=int(string_table[0][3]),
            failed_connections=int(string_table[0][4]),
            expiration_date=string_table[0][5],
        )
        if string_table
        else None
    )


# .
#   .--Connection rate-----------------------------------------------------.
#   |          ____                            _   _                       |
#   |         / ___|___  _ __  _ __   ___  ___| |_(_) ___  _ __            |
#   |        | |   / _ \| '_ \| '_ \ / _ \/ __| __| |/ _ \| '_ \           |
#   |        | |__| (_) | | | | | | |  __/ (__| |_| | (_) | | | |          |
#   |         \____\___/|_| |_|_| |_|\___|\___|\__|_|\___/|_| |_|          |
#   |                                                                      |
#   |                                    _                                 |
#   |                          _ __ __ _| |_ ___                           |
#   |                         | '__/ _` | __/ _ \                          |
#   |                         | | | (_| | ||  __/                          |
#   |                         |_|  \__,_|\__\___|                          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_safenet_ntls_connrate(section: Section) -> DiscoveryResult:
    if section:
        yield Service(item="successful")
        yield Service(item="failed")


def check_safenet_ntls_connrate(item: str, section: Section) -> CheckResult:
    now = time.time()

    match item:
        case "successful":
            item_data = section["successful_connections"]
        case "failed":
            item_data = section["failed_connections"]
        case _:
            return

    connections_rate = get_rate(
        get_value_store(),
        item,
        now,
        item_data,
        raise_overflow=True,
    )
    yield Metric("connections_rate", connections_rate)
    yield Result(state=State.OK, summary="%.2f connections/s" % connections_rate)


check_plugin_safenet_ntls_connrate = CheckPlugin(
    name="safenet_ntls_connrate",
    service_name="NTLS Connection Rate: %s",
    sections=["safenet_ntls"],
    discovery_function=inventory_safenet_ntls_connrate,
    check_function=check_safenet_ntls_connrate,
)

# .
#   .--Expiration date-----------------------------------------------------.
#   |           _____            _           _   _                         |
#   |          | ____|_  ___ __ (_)_ __ __ _| |_(_) ___  _ __              |
#   |          |  _| \ \/ / '_ \| | '__/ _` | __| |/ _ \| '_ \             |
#   |          | |___ >  <| |_) | | | | (_| | |_| | (_) | | | |            |
#   |          |_____/_/\_\ .__/|_|_|  \__,_|\__|_|\___/|_| |_|            |
#   |                     |_|                                              |
#   |                             _       _                                |
#   |                          __| | __ _| |_ ___                          |
#   |                         / _` |/ _` | __/ _ \                         |
#   |                        | (_| | (_| | ||  __/                         |
#   |                         \__,_|\__,_|\__\___|                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_safenet_ntls_expiration(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_safenet_ntls_expiration(section: Section) -> CheckResult:
    yield Result(
        state=State.OK,
        summary="The NTLS server certificate expires on " + section["expiration_date"],
    )


check_plugin_safenet_ntls_expiration = CheckPlugin(
    name="safenet_ntls_expiration",
    service_name="NTLS Expiration Date",
    sections=["safenet_ntls"],
    discovery_function=inventory_safenet_ntls_expiration,
    check_function=check_safenet_ntls_expiration,
)

# .
#   .--Links---------------------------------------------------------------.
#   |                       _     _       _                                |
#   |                      | |   (_)_ __ | | _____                         |
#   |                      | |   | | '_ \| |/ / __|                        |
#   |                      | |___| | | | |   <\__ \                        |
#   |                      |_____|_|_| |_|_|\_\___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_safenet_ntls_links(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_safenet_ntls_links(params: CheckParamT, section: Section) -> CheckResult:
    yield from check_levels(
        section["links"],
        metric_name="connections",
        render_func=lambda v: f"{v} links",
        levels_upper=params["levels"],
        label="Connections",
    )


check_plugin_safenet_ntls_links = CheckPlugin(
    name="safenet_ntls_links",
    service_name="NTLS Links",
    sections=["safenet_ntls"],
    discovery_function=inventory_safenet_ntls_links,
    check_function=check_safenet_ntls_links,
    check_ruleset_name="safenet_ntls_links",
    check_default_parameters=CheckParamT(levels=("no_levels", None)),
)

# .
#   .--Connected clients---------------------------------------------------.
#   |            ____                            _           _             |
#   |           / ___|___  _ __  _ __   ___  ___| |_ ___  __| |            |
#   |          | |   / _ \| '_ \| '_ \ / _ \/ __| __/ _ \/ _` |            |
#   |          | |__| (_) | | | | | | |  __/ (__| ||  __/ (_| |            |
#   |           \____\___/|_| |_|_| |_|\___|\___|\__\___|\__,_|            |
#   |                                                                      |
#   |                          _ _            _                            |
#   |                      ___| (_) ___ _ __ | |_ ___                      |
#   |                     / __| | |/ _ \ '_ \| __/ __|                     |
#   |                    | (__| | |  __/ | | | |_\__ \                     |
#   |                     \___|_|_|\___|_| |_|\__|___/                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_safenet_ntls_clients(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_safenet_ntls_clients(params: CheckParamT, section: Section) -> CheckResult:
    yield from check_levels(
        section["connected_clients"],
        metric_name="connections",
        levels_upper=params["levels"],
        render_func=lambda v: f"{v} connected clients",
        label="Connections",
    )


check_plugin_safenet_ntls_clients = CheckPlugin(
    name="safenet_ntls_clients",
    service_name="NTLS Clients",
    sections=["safenet_ntls"],
    discovery_function=inventory_safenet_ntls_clients,
    check_function=check_safenet_ntls_clients,
    check_ruleset_name="safenet_ntls_clients",
    check_default_parameters=CheckParamT(levels=("no_levels", None)),
)

# .
#   .--Operation status----------------------------------------------------.
#   |             ___                       _   _                          |
#   |            / _ \ _ __   ___ _ __ __ _| |_(_) ___  _ __               |
#   |           | | | | '_ \ / _ \ '__/ _` | __| |/ _ \| '_ \              |
#   |           | |_| | |_) |  __/ | | (_| | |_| | (_) | | | |             |
#   |            \___/| .__/ \___|_|  \__,_|\__|_|\___/|_| |_|             |
#   |                 |_|                                                  |
#   |                         _        _                                   |
#   |                     ___| |_ __ _| |_ _   _ ___                       |
#   |                    / __| __/ _` | __| | | / __|                      |
#   |                    \__ \ || (_| | |_| |_| \__ \                      |
#   |                    |___/\__\__,_|\__|\__,_|___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_safenet_ntls(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_safenet_ntls(
    section: Section,
) -> CheckResult:
    operation_status = section["operation_status"]
    if operation_status == "1":
        yield Result(state=State.OK, summary="Running")
    if operation_status == "2":
        yield Result(state=State.CRIT, summary="Down")
    if operation_status == "3":
        yield Result(state=State.UNKNOWN, summary="Unknown")


snmp_section_safenet_ntls = SimpleSNMPSection(
    name="safenet_ntls",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12383"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12383.3.1.2",
        oids=["1", "2", "3", "4", "5", "6"],
    ),
    parse_function=parse_safenet_ntls,
)

check_plugin_safenet_ntls = CheckPlugin(
    name="safenet_ntls",
    service_name="NTLS Operation Status",
    sections=["safenet_ntls"],
    discovery_function=inventory_safenet_ntls,
    check_function=check_safenet_ntls,
)
