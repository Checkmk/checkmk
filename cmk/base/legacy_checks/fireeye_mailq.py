#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.lib.fireeye import DETECT

check_info = {}

# .1.3.6.1.4.1.25597.13.1.44.0 0
# .1.3.6.1.4.1.25597.13.1.45.0 603
# .1.3.6.1.4.1.25597.13.1.46.0 8
# .1.3.6.1.4.1.25597.13.1.47.0 0
# .1.3.6.1.4.1.25597.13.1.48.0 96
# .1.3.6.1.4.1.25597.13.1.49.0 0


def parse_fireeye_mailq(string_table):
    if string_table:
        return dict(zip(["Deferred", "Hold", "Incoming", "Active", "Drop"], string_table[0]))
    return None


def dicsover_fireeye_mailq(section):
    yield None, {}


def check_fireeye_mailq(_no_item, params, parsed):
    for queue, value in parsed.items():
        yield check_levels(
            int(value),
            "mail_queue_%s_length" % queue.lower(),
            params.get(queue.lower()),
            human_readable_func=str,
            infoname="Mails in %s queue" % queue.lower(),
        )


check_info["fireeye_mailq"] = LegacyCheckDefinition(
    name="fireeye_mailq",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.13.1",
        oids=["44", "45", "47", "48", "49"],
    ),
    parse_function=parse_fireeye_mailq,
    service_name="Mail Queues",
    discovery_function=dicsover_fireeye_mailq,
    check_function=check_fireeye_mailq,
    check_ruleset_name="fireeye_mailq",
    check_default_parameters={
        "deferred": (1, 50),
        "hold": (500, 1000),
        "drop": (50, 500),
    },
)
