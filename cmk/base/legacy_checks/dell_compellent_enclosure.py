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
# .1.3.6.1.4.1.674.11000.2000.500.1.2.15.1.2.1 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.15.1.3.1 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.15.1.5.1 ""
# .1.3.6.1.4.1.674.11000.2000.500.1.2.15.1.6.1 "SAS_EBOD_6G"
# .1.3.6.1.4.1.674.11000.2000.500.1.2.15.1.7.1 "EN-SC4020"
# .1.3.6.1.4.1.674.11000.2000.500.1.2.15.1.9.1 "34QLD67"


def check_dell_compellent_enclosure(item, _no_params, info):
    for number, status, status_message, enc_type, model, serial in info:
        if number == item:
            state, state_readable = dell_compellent.dev_state_map(status)
            yield state, "Status: %s" % state_readable
            yield 0, f"Model: {model}, Type: {enc_type}, Service-Tag: {serial}"

            if status_message:
                yield state, "State Message: %s" % status_message


def parse_dell_compellent_enclosure(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_compellent_enclosure"] = LegacyCheckDefinition(
    name="dell_compellent_enclosure",
    parse_function=parse_dell_compellent_enclosure,
    detect=DETECT_DELL_COMPELLENT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.11000.2000.500.1.2.15.1",
        oids=["2", "3", "5", "6", "7", "9"],
    ),
    service_name="Enclosure %s",
    discovery_function=dell_compellent.discover,
    check_function=check_dell_compellent_enclosure,
)
