#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.fan import check_fan

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.plugins.lib.qnap import DETECT_QNAP

check_info = {}


def parse_qnap_fans(string_table):
    parsed = {}
    for fan, value in string_table:
        try:
            parsed[fan] = int(value.replace("RPM", ""))
        except ValueError:
            pass
    return parsed


def check_qnap_fans(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    yield check_fan(data, params)


def discover_qnap_fans(section):
    yield from ((item, {}) for item in section)


check_info["qnap_fans"] = LegacyCheckDefinition(
    name="qnap_fans",
    detect=DETECT_QNAP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.24681.1.2.15.1",
        oids=[OIDEnd(), "3"],
    ),
    parse_function=parse_qnap_fans,
    service_name="QNAP FAN %s",
    discovery_function=discover_qnap_fans,
    check_function=check_qnap_fans,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (2000, 1000),
    },
)
