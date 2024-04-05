#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.12356.101.4.2.1.0 27.00768(2015-09-01 15:10)
# .1.3.6.1.4.1.12356.101.4.2.2.0 6.00689(2015-09-01 00:15)

# signature ages (defaults are 1/2 days)

import time

from cmk.base.check_api import get_age_human_readable, LegacyCheckDefinition, regex
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.lib.fortinet import DETECT_FORTIGATE


def parse_fortigate_signatures(string_table):
    def parse_version(ver):
        # sample: 27.00768(2015-09-01 15:10)
        ver_regex = regex(r"([0-9.]*)\(([0-9-: ]*)\)")
        match = ver_regex.match(ver)
        if match is None:
            return None, None
        # what timezone is this in?
        t = time.strptime(match.group(2), "%Y-%m-%d %H:%M")
        ts = time.mktime(t)
        return match.group(1), time.time() - ts

    parsed = []
    for (key, title), value in zip(
        [
            ("av_age", "AV"),
            ("ips_age", "IPS"),
            ("av_ext_age", "AV extended"),
            ("ips_ext_age", "IPS extended"),
        ],
        string_table[0],
    ):
        version, age = parse_version(value)
        parsed.append((key, title, version, age))
    return parsed


def inventory_fortigate_signatures(parsed):
    if parsed:
        return [(None, {})]
    return []


def check_fortigate_signatures(_no_item, params, parsed):
    for key, title, version, age in parsed:
        if age is None:
            continue
        infotext = f"[{version}] {title} age: {get_age_human_readable(age)}"
        state = 0
        levels = params.get(key)
        if levels is not None:
            warn, crit = levels
            if crit is not None and age >= crit:
                state = 2
            elif warn is not None and age >= warn:
                state = 1
            if state:
                infotext += " (warn/crit at {}/{})".format(
                    get_age_human_readable(warn),
                    get_age_human_readable(crit),
                )
        yield state, infotext


check_info["fortigate_signatures"] = LegacyCheckDefinition(
    detect=DETECT_FORTIGATE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.101.4.2",
        oids=["1", "2", "3", "4"],
    ),
    parse_function=parse_fortigate_signatures,
    service_name="Signatures",
    discovery_function=inventory_fortigate_signatures,
    check_function=check_fortigate_signatures,
    check_ruleset_name="fortinet_signatures",
    check_default_parameters={
        "av_age": (86400, 172800),
        "ips_age": (86400, 172800),
    },
)
