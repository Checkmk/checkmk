#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree, StringTable
from cmk.plugins.acme.agent_based.lib import DETECT_ACME

check_info = {}

# .1.3.6.1.4.1.9148.3.9.1.10.1.3.65.1 rootca
# .1.3.6.1.4.1.9148.3.9.1.10.1.5.65.1 Jul 25 00:33:17 2003 GMT
# .1.3.6.1.4.1.9148.3.9.1.10.1.6.65.1 Aug 17 05:19:39 2027 GMT
# .1.3.6.1.4.1.9148.3.9.1.10.1.7.65.1 /C=US/O=Avaya Inc./OU=SIP Product Certificate Authority/CN=SIP Product Certificate Authority


def inventory_acme_certificates(info):
    return [(name, {}) for name, _start, _expire, _issuer in info]


def check_acme_certificates(item, params, info):
    for name, start, expire, issuer in info:
        if item == name:
            expire_date, _expire_tz = expire.rsplit(" ", 1)
            expire_time = time.mktime(time.strptime(expire_date, "%b %d %H:%M:%S %Y"))

            now = time.time()
            warn, crit = params["expire_lower"]
            state = 0

            time_diff = expire_time - now
            if time_diff < 0:
                age_info = "%s ago" % render.timespan(-time_diff)
            else:
                age_info = "%s to go" % render.timespan(time_diff)

            infotext = f"Expire: {expire} ({age_info})"

            if time_diff >= 0:
                if time_diff < crit:
                    state = 2
                elif time_diff < warn:
                    state = 1
                if state:
                    infotext += (
                        f" (warn/crit below {render.timespan(warn)}/{render.timespan(crit)})"
                    )
            else:
                state = 2
                infotext += " (expire date in the past)"

            yield state, infotext
            yield 0, f"Start: {start}, Issuer: {issuer}"


def parse_acme_certificates(string_table: StringTable) -> StringTable:
    return string_table


check_info["acme_certificates"] = LegacyCheckDefinition(
    name="acme_certificates",
    parse_function=parse_acme_certificates,
    detect=DETECT_ACME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9148.3.9.1.10.1",
        oids=["3", "5", "6", "7"],
    ),
    service_name="Certificate %s",
    discovery_function=inventory_acme_certificates,
    check_function=check_acme_certificates,
    check_ruleset_name="acme_certificates",
    check_default_parameters={
        "expire_lower": (604800, 2592000),  # 1 week, 30 days, suggested by customer
    },
)
