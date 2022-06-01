#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

F5_BIGIP_CLUSTER_CHECK_DEFAULT_PARAMETERS = {
    "type": "active_standby",
}


def _scan_is_f5_bigip(oid):
    return scan_f5_bigip(oid) and bool(oid(".1.3.6.1.4.1.3375.2.1.4.2.0"))


def _scan_version_pre_11_2(oid):
    version = oid(".1.3.6.1.4.1.3375.2.1.4.2.0")
    version_float = float(".".join(version.split(".")[:2]))
    return version_float < 11.2


def scan_f5_bigip(oid):
    return (
        ".1.3.6.1.4.1.3375.2" in oid(".1.3.6.1.2.1.1.2.0")
        and "big-ip" in oid(".1.3.6.1.4.1.3375.2.1.4.1.0", "").lower()
    )


def scan_f5_bigip_cluster_status_pre_11_2(oid):
    return _scan_is_f5_bigip(oid) and _scan_version_pre_11_2(oid)


def scan_f5_bigip_cluster_status_11_2_upwards(oid):
    return _scan_is_f5_bigip(oid) and not _scan_version_pre_11_2(oid)


def parse_f5_bigip_cluster_status(info):
    parsed = {}
    for node, status in info:
        parsed[node] = status
    return parsed


def inventory_f5_bigip_cluster_status(parsed):
    if parsed:
        yield None, None


def check_f5_bigip_cluster_status(_no_item, params, parsed, is_v11_2=False):
    if is_v11_2:
        node_states = ["unknown", "offline", "forced offline", "standby", "active"]
        active_value = "4"
    else:
        node_states = ["standby", "active 1", "active 2", "active"]
        active_value = "3"

    if params["type"] == "active_standby" and parsed.values().count(active_value) > 1:
        yield 2, "More than 1 node is active: "
    elif active_value not in parsed.values() and len(parsed) > 1:
        # Only applies if this check runs on a cluster
        yield 2, "No active node found: "

    for node in sorted(parsed):
        node_name = ("[%s] " % node) if node else ""
        node_state = parsed[node]
        state = 0
        if is_v11_2:
            if node_state in params.get("v11_2_states", []):
                state = params["v11_2_states"][node_state]
            else:
                state = {
                    "0": 3,
                    "1": 2,
                    "2": 2,
                    "3": 0,
                    "4": 0,
                }[node_state]
        yield state, "Node %sis %s" % (node_name, node_states[int(node_state)])
