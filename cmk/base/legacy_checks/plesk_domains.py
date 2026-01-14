#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_plesk_domains(info):
    if info and info[0]:
        return [(None, None)]
    return None


def check_plesk_domains(_no_item, _no_params, info):
    if not info:
        return (1, "No domains configured")
    return (0, "%s" % ",\n".join([i[0] for i in info]))


def parse_plesk_domains(string_table: StringTable) -> StringTable:
    return string_table


check_info["plesk_domains"] = LegacyCheckDefinition(
    name="plesk_domains",
    parse_function=parse_plesk_domains,
    service_name="Plesk Domains",
    discovery_function=discover_plesk_domains,
    check_function=check_plesk_domains,
)
