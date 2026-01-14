#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# .1.3.6.1.4.1.20632.2.5 2


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree, StringTable
from cmk.plugins.barracuda.lib import DETECT_BARRACUDA

check_info = {}


def discover_barracuda_mail_latency(info):
    yield None, {}


def check_barracuda_mail_latency(_no_item, params, info):
    return check_levels(
        int(info[0][0]),
        "mail_latency",
        params["levels"],
        human_readable_func=render.timespan,
        infoname="Average",
    )


def parse_barracuda_mail_latency(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["barracuda_mail_latency"] = LegacyCheckDefinition(
    name="barracuda_mail_latency",
    parse_function=parse_barracuda_mail_latency,
    detect=DETECT_BARRACUDA,
    # The barracuda spam firewall does not response or returns a timeout error
    # executing 'snmpwalk' on whole tables. But we can workaround here specifying
    # all needed OIDs. Then we can use 'snmpget' and 'snmpwalk' on these single OIDs.,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20632.2",
        oids=["5"],
    ),
    service_name="Mail Latency",
    discovery_function=discover_barracuda_mail_latency,
    check_function=check_barracuda_mail_latency,
    check_ruleset_name="mail_latency",
    check_default_parameters={
        # Suggested by customer, in seconds
        "levels": (40, 60),
    },
)
