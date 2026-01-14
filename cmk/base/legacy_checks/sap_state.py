#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_sap_state(info):
    for line in info:
        if len(line) == 2:
            yield line[0], None


def check_sap_state(item, _no_parameters, info):
    def value_to_status(value):
        if value == "OK":
            return 0
        return 2

    for line in info:
        if line[0] == item:
            value = line[1]
            return value_to_status(value), "Status: %s" % value


def parse_sap_state(string_table: StringTable) -> StringTable:
    return string_table


check_info["sap_state"] = LegacyCheckDefinition(
    name="sap_state",
    parse_function=parse_sap_state,
    service_name="SAP State %s",
    discovery_function=discover_sap_state,
    check_function=check_sap_state,
)
