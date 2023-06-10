#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.couchbase import parse_couchbase_lines


def check_couchbase_nodes_status(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    health = data.get("status")
    if health is not None:
        status = 0
        if health == "warmup":
            status = params.get("warmup_state", 0)
        if health == "unhealthy":
            status = params.get("unhealthy_state", 2)
        yield status, "Health: %s" % health

    for key, label in (
        ("otpNode", "One-time-password node"),
        ("recoveryType", "Recovery type"),
        ("version", "Version"),
        ("clusterCompatibility", "Cluster compatibility"),
    ):
        yield 0, "%s: %s" % (label, data.get(key, "unknown"))

    membership = data.get("clusterMembership")
    if membership is None:
        return

    status = 0
    if membership == "inactiveAdded":
        status = params.get("inactive_added_state", 1)
    elif membership == "inactiveFailed":
        status = params.get("inactive_added_state", 2)
    yield status, "Cluster membership: %s" % membership


def discover_couchbase_nodes_info(section):
    yield from ((item, {}) for item in section)


check_info["couchbase_nodes_info"] = LegacyCheckDefinition(
    parse_function=parse_couchbase_lines,
    discovery_function=discover_couchbase_nodes_info,
    check_function=check_couchbase_nodes_status,
    service_name="Couchbase %s Info",
    check_ruleset_name="couchbase_status",
)
