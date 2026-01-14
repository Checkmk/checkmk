#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.qnap.lib import DETECT_QNAP

check_info = {}


def discover_qnap_disks(info):
    return [(x[0], None) for x in info if x[2] != "-5"]


def check_qnap_disks(item, _no_params, info):
    map_states = {
        "0": (0, "ready"),
        "-4": (2, "unknown"),
        "-5": (2, "no disk"),
        "-6": (2, "invalid"),
        "-9": (2, "read write error"),
    }

    for desc, temp, status, model, size, cond in info:
        if desc == item:
            state, state_readable = map_states.get(status, (3, "unknown"))
            yield state, f"Status: {state_readable} ({cond})"

            if "--" in cond:
                yield 1, "SMART Information missing"
            elif cond != "GOOD":
                yield 1, "SMART Warnings"

            yield 0, f"Model: {model}, Temperature: {temp}, Size: {size}"


def parse_qnap_disks(string_table: StringTable) -> StringTable:
    return string_table


check_info["qnap_disks"] = LegacyCheckDefinition(
    name="qnap_disks",
    parse_function=parse_qnap_disks,
    detect=DETECT_QNAP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.24681.1.2.11.1",
        oids=["2", "3", "4", "5", "6", "7"],
    ),
    service_name="Disk %s",
    discovery_function=discover_qnap_disks,
    check_function=check_qnap_disks,
)
