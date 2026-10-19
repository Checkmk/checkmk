#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Huawei switches that report the enterprise number 56813 (Dongguan Huarong) instead of 2011.

The tree below the enterprise number is the same, so each section here fetches the same columns
as its 2011 counterpart and feeds the parsed section of the existing check.
"""

from collections.abc import Sequence

from cmk.agent_based.v2 import SNMPSection, StringTable
from cmk.plugins.lib.huawei import (
    HUARONG_ENTERPRISE,
    parse_huawei_physical_entity_values,
    Section,
)


def parse_huawei_switch_entity_values(string_table: Sequence[StringTable]) -> Section:
    return parse_huawei_physical_entity_values(string_table)


snmp_section_huawei_switch_cpu_huarong = SNMPSection(
    name="huawei_switch_cpu_huarong",
    parsed_section_name="huawei_switch_cpu",
    detect=HUARONG_ENTERPRISE.switch_detect,
    fetch=HUARONG_ENTERPRISE.entity_state_trees("5"),
    parse_function=parse_huawei_switch_entity_values,
)

snmp_section_huawei_switch_mem_huarong = SNMPSection(
    name="huawei_switch_mem_huarong",
    parsed_section_name="huawei_switch_mem",
    detect=HUARONG_ENTERPRISE.switch_detect,
    fetch=HUARONG_ENTERPRISE.entity_state_trees("7"),
    parse_function=parse_huawei_switch_entity_values,
)
