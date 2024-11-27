#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.20632.2.2  0
# .1.3.6.1.4.1.20632.2.3  19
# .1.3.6.1.4.1.20632.2.4  17
# .1.3.6.1.4.1.20632.2.60 434

# Suggested by customer

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.barracuda import DETECT_BARRACUDA

check_info = {}


def discover_barracuda_mailqueues(info):
    yield None, {}


def check_barracuda_mailqueues(_no_item, params, info):
    in_queue_str, active_queue_str, deferred_queue_str, daily_sent = info[0]
    for queue_type, queue in [
        ("Active", int(active_queue_str)),
        ("Deferred", int(deferred_queue_str)),
    ]:
        state = 0
        infotext = f"{queue_type}: {queue}"
        warn, crit = params[queue_type.lower()]

        if queue >= crit:
            state = 2
        elif queue >= warn:
            state = 1
        if state:
            infotext += " (warn/crit at %d/%d %s mails)" % (warn, crit, queue_type.lower())

        yield state, infotext, [("mail_queue_%s_length" % queue_type.lower(), queue, warn, crit)]

    yield 0, "Incoming: %s" % in_queue_str
    if daily_sent:
        yield 0, "Daily sent: %s" % daily_sent


def parse_barracuda_mailqueues(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["barracuda_mailqueues"] = LegacyCheckDefinition(
    name="barracuda_mailqueues",
    parse_function=parse_barracuda_mailqueues,
    detect=DETECT_BARRACUDA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20632.2",
        oids=["2", "3", "4", "60"],
    ),
    service_name="Mail Queue",
    # The barracuda spam firewall does not response or returns a timeout error
    # executing 'snmpwalk' on whole tables. But we can workaround here specifying
    # all needed OIDs. Then we can use 'snmpget' and 'snmpwalk' on these single OIDs.,
    discovery_function=discover_barracuda_mailqueues,
    check_function=check_barracuda_mailqueues,
    check_ruleset_name="mail_queue_length_single",
    check_default_parameters={
        "deferred": (80, 100),
        "active": (80, 100),
    },
)
