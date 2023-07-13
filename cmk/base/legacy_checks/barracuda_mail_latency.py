#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.20632.2.5 2

# Suggested by customer, in seconds


from cmk.base.check_api import get_age_human_readable, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.barracuda import DETECT_BARRACUDA

barracuda_mail_latency_default_levels = (40, 60)


def inventory_barracuda_mail_latency(info):
    return [(None, barracuda_mail_latency_default_levels)]


def check_barracuda_mail_latency(_no_item, params, info):
    avg_mail_latency = int(info[0][0])
    state = 0
    infotext = "Average: %s" % get_age_human_readable(avg_mail_latency)

    warn, crit = params
    if avg_mail_latency >= crit:
        state = 2
    elif avg_mail_latency >= warn:
        state = 1
    if state:
        infotext += " (warn/crit at %s/%s)" % (
            get_age_human_readable(warn),
            get_age_human_readable(crit),
        )

    return state, infotext, [("mail_latency", avg_mail_latency, warn, crit)]


check_info["barracuda_mail_latency"] = LegacyCheckDefinition(
    detect=DETECT_BARRACUDA,
    # The barracuda spam firewall does not response or returns a timeout error
    # executing 'snmpwalk' on whole tables. But we can workaround here specifying
    # all needed OIDs. Then we can use 'snmpget' and 'snmpwalk' on these single OIDs.,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20632.2",
        oids=["5"],
    ),
    service_name="Mail Latency",
    discovery_function=inventory_barracuda_mail_latency,
    check_function=check_barracuda_mail_latency,
    check_ruleset_name="mail_latency",
)
