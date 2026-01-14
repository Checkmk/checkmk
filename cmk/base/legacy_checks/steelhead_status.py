#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.steelhead.lib import DETECT_STEELHEAD

check_info = {}


def discover_steelhead_status(info):
    if len(info) == 1:
        yield None, {}


def check_steelhead_status(item, params, info):
    health, status = info[0]
    if health == "Healthy" and status == "running":
        return (0, "Healthy and running")
    return (2, f"Status is {health} and {status}")


def parse_steelhead_status(string_table: StringTable) -> StringTable:
    return string_table


check_info["steelhead_status"] = LegacyCheckDefinition(
    name="steelhead_status",
    parse_function=parse_steelhead_status,
    detect=DETECT_STEELHEAD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.17163.1.1.2",
        oids=["2", "3"],
    ),
    service_name="Status",
    discovery_function=discover_steelhead_status,
    check_function=check_steelhead_status,
)
