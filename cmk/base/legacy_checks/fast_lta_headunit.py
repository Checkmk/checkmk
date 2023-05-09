#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import all_of, any_of, exists, startswith
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

fast_lta_headunit_info = [
    (".1.3.6.1.4.1.27417.2", [1, 2, 5])  # headUnitStatus  # replicationMode  # replicationRunning
]


#   .--status--------------------------------------------------------------.
#   |                         _        _                                   |
#   |                     ___| |_ __ _| |_ _   _ ___                       |
#   |                    / __| __/ _` | __| | | / __|                      |
#   |                    \__ \ || (_| | |_| |_| \__ \                      |
#   |                    |___/\__\__,_|\__|\__,_|___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_fast_lta_headunit_status(info):
    if len(info[0]) > 0:
        return [(None, None)]
    return []


def check_fast_lta_headunit_status(item, _no_params, info):
    try:
        head_unit_status, app_read_only_status = info[0][0][:2]
    except IndexError:
        return None

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
        status = 0
    elif head_unit_status == "70" and app_read_only_status == "0":
        # on Slave node appReadOnly is also an ok state
        status = 0
    else:
        status = 2

    if head_unit_status in head_unit_status_map:
        message = "Head Unit status is %s." % head_unit_status_map[head_unit_status]
    else:
        message = "Head Unit status is %s." % head_unit_status

    return status, message


check_info["fast_lta_headunit.status"] = {
    "detect": all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        any_of(exists(".1.3.6.1.4.1.27417.2.1"), exists(".1.3.6.1.4.1.27417.2.1.0")),
    ),
    "check_function": check_fast_lta_headunit_status,
    "discovery_function": inventory_fast_lta_headunit_status,
    "service_name": "Fast LTA Headunit Status",
    "fetch": [
        SNMPTree(
            base=".1.3.6.1.4.1.27417.2",
            oids=["1", "2", "5"],
        )
    ],
}

# .
#   .--replication---------------------------------------------------------.
#   |                          _ _           _   _                         |
#   |           _ __ ___ _ __ | (_) ___ __ _| |_(_) ___  _ __              |
#   |          | '__/ _ \ '_ \| | |/ __/ _` | __| |/ _ \| '_ \             |
#   |          | | |  __/ |_) | | | (_| (_| | |_| | (_) | | | |            |
#   |          |_|  \___| .__/|_|_|\___\__,_|\__|_|\___/|_| |_|            |
#   |                   |_|                                                |
#   '----------------------------------------------------------------------'


def inventory_fast_lta_headunit_replication(info):
    if len(info[0]) > 0:
        return [(None, None)]
    return []


def check_fast_lta_headunit_replication(item, _no_params, info):
    try:
        node_replication_mode, replication_status = info[0][0][1:3]
    except IndexError:
        return None

    head_unit_replication_map = {
        "0": "Slave",
        "1": "Master",
        "255": "standalone",
    }

    if replication_status == "1":
        message = "Replication is running."
        status = 0
    else:
        message = "Replication is not running (!!)."
        status = 2

    if node_replication_mode in head_unit_replication_map:
        message += " This node is %s." % head_unit_replication_map[node_replication_mode]
    else:
        message += " Replication mode of this node is %s." % node_replication_mode

    return status, message


check_info["fast_lta_headunit.replication"] = {
    "detect": all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        any_of(exists(".1.3.6.1.4.1.27417.2.1"), exists(".1.3.6.1.4.1.27417.2.1.0")),
    ),
    "check_function": check_fast_lta_headunit_replication,
    "discovery_function": inventory_fast_lta_headunit_replication,
    "service_name": "Fast LTA Replication",
    "fetch": [
        SNMPTree(
            base=".1.3.6.1.4.1.27417.2",
            oids=["1", "2", "5"],
        )
    ],
}

# .
