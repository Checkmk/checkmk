#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, contains, not_equals, OIDEnd, SNMPTree
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

check_info = {}

#
# monitoring of cluster members (nodes) in fortigate high availability tree
#

# cluster info
# .1.3.6.1.4.1.12356.101.13.1.1.0 3
# .1.3.6.1.4.1.12356.101.13.1.7.0 DEPTHA-HA

# node info
# .1.3.6.1.4.1.12356.101.13.2.1.1.11.1 NODE-01
# .1.3.6.1.4.1.12356.101.13.2.1.1.11.2 NODE-02
# .1.3.6.1.4.1.12356.101.13.2.1.1.3.1 13
# .1.3.6.1.4.1.12356.101.13.2.1.1.3.2 1
# .1.3.6.1.4.1.12356.101.13.2.1.1.4.1 52
# .1.3.6.1.4.1.12356.101.13.2.1.1.4.2 21
# .1.3.6.1.4.1.12356.101.13.2.1.1.6.1 1884
# .1.3.6.1.4.1.12356.101.13.2.1.1.6.2 742

# only one node given => standalone cluster
# .1.3.6.1.4.1.12356.101.13.2.1.1.11.1  ""
# .1.3.6.1.4.1.12356.101.13.2.1.1.3.1  0
# .1.3.6.1.4.1.12356.101.13.2.1.1.4.1  19
# .1.3.6.1.4.1.12356.101.13.2.1.1.6.1  443

#   .--Info----------------------------------------------------------------.
#   |                         ___        __                                |
#   |                        |_ _|_ __  / _| ___                           |
#   |                         | || '_ \| |_ / _ \                          |
#   |                         | || | | |  _| (_) |                         |
#   |                        |___|_| |_|_|  \___/                          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def parse_fortigate_node(string_table):
    parsed: dict = {"nodes": {}}
    if string_table[0]:
        parsed["cluster_info"] = string_table[0][0]

    for hostname, cpu_str, memory_str, sessions_str, oid_end in string_table[1]:
        # This means we have a standalone cluster
        if len(string_table[1]) == 1:
            item_name = "Cluster"
        elif hostname:
            item_name = hostname
        else:
            item_name = "Node %s" % oid_end

        parsed["nodes"].setdefault(
            item_name,
            {
                "cpu": float(cpu_str),
                "memory": int(memory_str),
                "sessions": int(sessions_str),
            },
        )

    return parsed


def discover_fortigate_cluster(parsed):
    if "cluster_info" in parsed:
        return [(None, None)]
    return []


def check_fortigate_cluster(_no_item, _no_params, parsed):
    map_mode = {
        "1": "Standalone",
        "2": "Active/Active",
        "3": "Active/Passive",
    }

    if "cluster_info" in parsed:
        system_mode, group_name = parsed["cluster_info"]
        return 0, f"System mode: {map_mode[system_mode]}, Group: {group_name}"
    return None


check_info["fortigate_node"] = LegacyCheckDefinition(
    name="fortigate_node",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.101.1"),
        not_equals(".1.3.6.1.4.1.12356.101.13.1.1.0", "1"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.12356.101.13.1",
            oids=["1", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.12356.101.13.2.1.1",
            oids=["11", "3", "4", "6", OIDEnd()],
        ),
    ],
    parse_function=parse_fortigate_node,
    service_name="Cluster Info",
    discovery_function=discover_fortigate_cluster,
    check_function=check_fortigate_cluster,
)

# .
#   .--CPU-----------------------------------------------------------------.
#   |                           ____ ____  _   _                           |
#   |                          / ___|  _ \| | | |                          |
#   |                         | |   | |_) | | | |                          |
#   |                         | |___|  __/| |_| |                          |
#   |                          \____|_|    \___/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_fortigate_node_cpu(section):
    for hostname in section["nodes"]:
        yield hostname, {}


def check_fortigate_node_cpu(item, params, parsed):
    if item in parsed["nodes"]:
        return check_cpu_util(parsed["nodes"][item]["cpu"], params["levels"])
    return None


check_info["fortigate_node.cpu"] = LegacyCheckDefinition(
    name="fortigate_node_cpu",
    service_name="CPU utilization %s",
    sections=["fortigate_node"],
    discovery_function=discover_fortigate_node_cpu,
    check_function=check_fortigate_node_cpu,
    check_default_parameters={"levels": (80.0, 90.0)},
)

# .
#   .--Sessions------------------------------------------------------------.
#   |                ____                _                                 |
#   |               / ___|  ___  ___ ___(_) ___  _ __  ___                 |
#   |               \___ \ / _ \/ __/ __| |/ _ \| '_ \/ __|                |
#   |                ___) |  __/\__ \__ \ | (_) | | | \__ \                |
#   |               |____/ \___||___/___/_|\___/|_| |_|___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_fortigate_node_ses(parsed):
    for hostname in parsed["nodes"]:
        yield hostname, {}


def check_fortigate_node_ses(item, params, parsed):
    if (data := parsed["nodes"].get(item)) is None:
        return

    yield check_levels(
        data["sessions"], "session", params["levels"], human_readable_func=str, infoname="Sessions"
    )


check_info["fortigate_node.sessions"] = LegacyCheckDefinition(
    name="fortigate_node_sessions",
    service_name="Sessions %s",
    sections=["fortigate_node"],
    discovery_function=discover_fortigate_node_ses,
    check_function=check_fortigate_node_ses,
    check_ruleset_name="fortigate_node_sessions",
    check_default_parameters={"levels": (100000, 150000)},
)
