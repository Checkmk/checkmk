#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<heartbeat_rscstatus>>>
# all
#
# Status can be "local", "foreign", "all" or "none"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def parse_heartbeat_rscstatus(string_table):
    try:
        return string_table[0][0]
    except IndexError:
        return None


def discover_heartbeat_rscstatus(heartbeat_rsc_status):
    if heartbeat_rsc_status is not None:
        yield None, {"discovered_state": heartbeat_rsc_status}


def check_heartbeat_rscstatus(_no_item, params, heartbeat_rsc_status):
    if heartbeat_rsc_status is None:
        return

    if not isinstance(params, dict):
        # old params comes styled with double qoutes
        params = {"discovered_state": params.replace('"', "")}

    expected_state = params.get("discovered_state")
    if "expected_state" in params:
        expected_state = params["expected_state"]

    if expected_state == heartbeat_rsc_status:
        yield 0, "Current state: %s" % heartbeat_rsc_status
    else:
        yield 2, f"Current state: {heartbeat_rsc_status} (Expected: {expected_state})"


check_info["heartbeat_rscstatus"] = LegacyCheckDefinition(
    name="heartbeat_rscstatus",
    parse_function=parse_heartbeat_rscstatus,
    service_name="Heartbeat Ressource Status",
    discovery_function=discover_heartbeat_rscstatus,
    check_function=check_heartbeat_rscstatus,
    check_ruleset_name="heartbeat_rscstatus",
)
