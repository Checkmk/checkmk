#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes import dell_compellent
from cmk.plugins.lib.dell import DETECT_DELL_COMPELLENT

check_info = {}

# example output
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.2.1 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.2.2 2
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.3.1 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.3.2 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.4.1 "Controller A"
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.4.2 "Controller B"
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.5.1 "10.20.30.41"
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.5.2 "10.20.30.42"
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.7.1 "CT_SC4020"
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.7.2 "CT_SC4020"


def check_dell_compellent_controller(item, _no_params, info):
    for number, status, name, addr, model in info:
        if number == item:
            state, state_readable = dell_compellent.dev_state_map(status)
            yield state, "Status: %s" % state_readable
            yield 0, f"Model: {model}, Name: {name}, Address: {addr}"


def parse_dell_compellent_controller(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_compellent_controller"] = LegacyCheckDefinition(
    name="dell_compellent_controller",
    parse_function=parse_dell_compellent_controller,
    detect=DETECT_DELL_COMPELLENT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.11000.2000.500.1.2.13.1",
        oids=["2", "3", "4", "5", "7"],
    ),
    service_name="Controller %s",
    discovery_function=dell_compellent.discover,
    check_function=check_dell_compellent_controller,
)
