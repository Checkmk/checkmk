#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, get_rate, get_value_store, SNMPTree, startswith

check_info = {}


def parse_safenet_ntls(string_table):
    return (
        {
            "operation_status": string_table[0][0],
            "connected_clients": int(string_table[0][1]),
            "links": int(string_table[0][2]),
            "successful_connections": int(string_table[0][3]),
            "failed_connections": int(string_table[0][4]),
            "expiration_date": string_table[0][5],
        }
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


def inventory_safenet_ntls_connrate(parsed):
    if parsed:
        yield "successful", None
        yield "failed", None


def check_safenet_ntls_connrate(item, _no_params, parsed):
    now = time.time()
    connections_rate = get_rate(
        get_value_store(), item, now, parsed[item + "_connections"], raise_overflow=True
    )
    perfdata = [("connections_rate", connections_rate)]
    return 0, "%.2f connections/s" % connections_rate, perfdata


check_info["safenet_ntls.connrate"] = LegacyCheckDefinition(
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


def inventory_safenet_ntls_expiration(parsed):
    if parsed:
        return [(None, None)]
    return []


def check_safenet_ntls_expiration(_no_item, _no_params, parsed):
    return 0, "The NTLS server certificate expires on " + parsed["expiration_date"]


check_info["safenet_ntls.expiration"] = LegacyCheckDefinition(
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


def inventory_safenet_ntls_links(parsed):
    if parsed:
        yield None, {}


def check_safenet_ntls_links(_no_item, params, parsed):
    # NOTE: these can be predictive levels!
    return check_levels(
        parsed["links"], "connections", params["levels"], unit="links", infoname="Connections"
    )


check_info["safenet_ntls.links"] = LegacyCheckDefinition(
    name="safenet_ntls_links",
    service_name="NTLS Links",
    sections=["safenet_ntls"],
    discovery_function=inventory_safenet_ntls_links,
    check_function=check_safenet_ntls_links,
    check_ruleset_name="safenet_ntls_links",
    check_default_parameters={"levels": None},
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


def inventory_safenet_ntls_clients(parsed):
    if parsed:
        yield None, {}


def check_safenet_ntls_clients(_no_item, params, parsed):
    # NOTE: these can be predictive levels!
    yield check_levels(
        parsed["connected_clients"],
        "connections",
        params["levels"],
        unit="connected clients",
        infoname="Connections",
    )


check_info["safenet_ntls.clients"] = LegacyCheckDefinition(
    name="safenet_ntls_clients",
    service_name="NTLS Clients",
    sections=["safenet_ntls"],
    discovery_function=inventory_safenet_ntls_clients,
    check_function=check_safenet_ntls_clients,
    check_ruleset_name="safenet_ntls_clients",
    check_default_parameters={"levels": None},
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


def inventory_safenet_ntls(parsed):
    if parsed:
        return [(None, None)]
    return []


def check_safenet_ntls(_no_item, _no_params, parsed):
    operation_status = parsed["operation_status"]
    if operation_status == "1":
        return 0, "Running"
    if operation_status == "2":
        return 2, "Down"
    if operation_status == "3":
        return 3, "Unknown"
    return None


check_info["safenet_ntls"] = LegacyCheckDefinition(
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
    service_name="NTLS Operation Status",
    discovery_function=inventory_safenet_ntls,
    check_function=check_safenet_ntls,
)
