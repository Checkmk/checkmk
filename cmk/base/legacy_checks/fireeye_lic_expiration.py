#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.fireeye.lib import DETECT

check_info = {}


def discover_fireeye_lic_expiration(info):
    for line in info:
        if line[1]:
            yield line[0], {}


def check_fireeye_lic_expiration(item, params, info):
    for feature, days in info:
        if feature == item:
            warn, crit = params.get("days")
            infotext = "Days remaining: %s" % days
            seconds = int(days) * 24 * 60 * 60
            perfdata = [("lifetime_remaining", seconds, warn, crit)]
            if int(days) > warn:
                yield 0, infotext, perfdata
            elif int(days) > crit:
                yield 1, infotext + " (warn/crit at %d/%d days)" % (warn, crit), perfdata
            else:
                yield 2, infotext + " (warn/crit at %d/%d days)" % (warn, crit), perfdata


def parse_fireeye_lic_expiration(string_table: StringTable) -> StringTable:
    return string_table


check_info["fireeye_lic_expiration"] = LegacyCheckDefinition(
    name="fireeye_lic_expiration",
    parse_function=parse_fireeye_lic_expiration,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.5.1.16.1",
        oids=["1", "5"],
    ),
    service_name="License Expiration %s",
    discovery_function=discover_fireeye_lic_expiration,
    check_function=check_fireeye_lic_expiration,
    check_ruleset_name="fireeye_lic",
    check_default_parameters={
        "days": (120, 90),
    },
)
