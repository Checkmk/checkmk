#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Nikolas Hagemann, comNET GmbH - nikolas.hagemann@comnetgmbh.com

# Example output:
# .1.3.6.1.4.1.12356.118.5.1.1.0 0
# .1.3.6.1.4.1.12356.118.5.1.2.0 0
# .1.3.6.1.4.1.12356.118.5.1.3.0 0
# .1.3.6.1.4.1.12356.118.5.1.4.0 0
# .1.3.6.1.4.1.12356.118.5.1.5.0 0
# .1.3.6.1.4.1.12356.118.5.1.6.0 0
# .1.3.6.1.4.1.12356.118.5.1.7.0 0
# .1.3.6.1.4.1.12356.118.5.1.8.0 0
# .1.3.6.1.4.1.12356.118.5.1.9.0 0
# .1.3.6.1.4.1.12356.118.5.1.10.0 0
# .1.3.6.1.4.1.12356.118.5.1.11.0 0


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.fortinet.lib import DETECT_FORTISANDBOX

check_info = {}


def parse_fortisandbox_queues(string_table):
    queues = [
        "Executable",
        "PDF",
        "Office",
        "Flash",
        "Web",
        "Android",
        "MAC",
        "URL job",
        "User defined",
        "Non Sandboxing",
        "Job Queue Assignment",
    ]

    return {k: int(v) for k, v in zip(queues, string_table[0])} if string_table else None


def discover_fortisandbox_queues(parsed):
    for queue in parsed:
        yield queue, {}


def check_fortisandbox_queues(item, params, parsed):
    for queue, length in parsed.items():
        if queue == item:
            warn, crit = params.get("length", (None, None))
            state = 0
            if crit and length >= crit:
                state = 2
            elif warn and length >= warn:
                state = 1
            perfdata = [("queue", length, warn, crit)]
            infotext = "Queue length: %s" % length
            if state:
                infotext += f" (warn/crit at {warn}/{crit})"
            return state, infotext, perfdata
    return None


check_info["fortisandbox_queues"] = LegacyCheckDefinition(
    name="fortisandbox_queues",
    detect=DETECT_FORTISANDBOX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.118.5.1",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
    ),
    parse_function=parse_fortisandbox_queues,
    service_name="Pending %s files",
    discovery_function=discover_fortisandbox_queues,
    check_function=check_fortisandbox_queues,
    check_ruleset_name="fortisandbox_queues",
)
