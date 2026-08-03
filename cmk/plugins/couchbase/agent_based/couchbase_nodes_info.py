#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines, Section


def check_couchbase_nodes_status(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    health = data.get("status")
    if health is not None:
        status = State.OK
        if health == "warmup":
            status = State(params.get("warmup_state", 0))
        if health == "unhealthy":
            status = State(params.get("unhealthy_state", 2))
        yield Result(state=status, summary="Health: %s" % health)

    for key, label in (
        ("otpNode", "One-time-password node"),
        ("recoveryType", "Recovery type"),
        ("version", "Version"),
        ("clusterCompatibility", "Cluster compatibility"),
    ):
        yield Result(state=State.OK, summary="{}: {}".format(label, data.get(key, "unknown")))

    membership = data.get("clusterMembership")
    if membership is None:
        return

    mem_status = State.OK
    if membership == "inactiveAdded":
        mem_status = State(params.get("inactive_added_state", 1))
    elif membership == "inactiveFailed":
        mem_status = State(params.get("inactive_added_state", 2))
    yield Result(state=mem_status, summary="Cluster membership: %s" % membership)


def discover_couchbase_nodes_info(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


agent_section_couchbase_nodes_info = AgentSection(
    name="couchbase_nodes_info",
    parse_function=parse_couchbase_lines,
)


check_plugin_couchbase_nodes_info = CheckPlugin(
    name="couchbase_nodes_info",
    service_name="Couchbase %s Info",
    discovery_function=discover_couchbase_nodes_info,
    check_function=check_couchbase_nodes_status,
    check_ruleset_name="couchbase_status",
    check_default_parameters={},
)
