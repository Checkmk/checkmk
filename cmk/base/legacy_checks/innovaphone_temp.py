#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}


def discover_innovaphone_temp(info):
    yield "Ambient", {}


def check_innovaphone_temp(item, params, info):
    return check_temperature(int(info[0][1]), params, "innovaphone_temp_%s" % item)


def parse_innovaphone_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["innovaphone_temp"] = LegacyCheckDefinition(
    name="innovaphone_temp",
    parse_function=parse_innovaphone_temp,
    service_name="Temperature %s",
    discovery_function=discover_innovaphone_temp,
    check_function=check_innovaphone_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (45.0, 50.0)},
)
