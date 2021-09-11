#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.4123 System Status
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.4123 Normal with Warning
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.4240 System Model Number
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.4240 Liebert HPC
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.4706 Unit Operating State
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.4706 standby
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5074 Unit Operating State Reason
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5074 Reason Unknown

from typing import Dict, List

from .agent_based_api.v1 import register, Result, Service, SNMPTree
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.liebert import DETECT_LIEBERT, parse_liebert_without_unit

ParsedSection = Dict[str, str]


def parse_liebert_system(string_table: List[StringTable]) -> ParsedSection:
    return parse_liebert_without_unit(string_table, str)


def discover_liebert_system(section: ParsedSection) -> DiscoveryResult:
    model = section.get("System Model Number")
    if model:
        yield Service(item=model)


def check_liebert_system(item: str, section: ParsedSection) -> CheckResult:
    # Variable 'item' is used to generate the service description.
    # However, only one item per host is expected, which is why it is not
    # used in this check funtion.
    for key, value in sorted(section.items()):
        if key == "System Status" and "Normal Operation" not in value:
            yield Result(state=state.CRIT, summary="%s: %s" % (key, value))
        else:
            yield Result(state=state.OK, summary="%s: %s" % (key, value))


register.snmp_section(
    name="liebert_system",
    detect=DETECT_LIEBERT,
    parse_function=parse_liebert_system,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
            oids=[
                "10.1.2.1.4123",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
                "20.1.2.1.4123",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
                "10.1.2.1.4240",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
                "20.1.2.1.4240",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
                "10.1.2.1.4706",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
                "20.1.2.1.4706",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
                "10.1.2.1.5074",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryDataLabel
                "20.1.2.1.5074",  # LIEBERT-GP-FLExible-MIB: lgpFlexibleEntryValue
            ],
        ),
    ],
)

register.check_plugin(
    name="liebert_system",
    service_name="Status %s",
    discovery_function=discover_liebert_system,
    check_function=check_liebert_system,
)
