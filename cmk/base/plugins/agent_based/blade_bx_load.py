#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from .agent_based_api.v1 import contains, register, Service, SNMPTree
from .agent_based_api.v1.type_defs import DiscoveryResult, StringTable
from .utils.cpu import Load, Section
from .utils.cpu_load import check_cpu_load


def parse_blade_bx_load(string_table: StringTable) -> Optional[Section]:
    """
    >>> parse_blade_bx_load([])
    >>> parse_blade_bx_load([["0.210000"], ["0.190000"], ["0.280000"]])
    Section(load=Load(load1=0.21, load5=0.19, load15=0.28), num_cpus=1, threads=None, type=<ProcessorType.unspecified: 0>)
    """
    return (
        Section(
            load=Load(
                *(float(sub_table[0]) for sub_table in string_table),
            ),
            num_cpus=1,
        )
        if string_table
        else None
    )


register.snmp_section(
    name="blade_bx_load",
    parse_function=parse_blade_bx_load,
    # Note: I'm not sure if this check is working at all. If yes,
    # then the SNMP implementation of that device must be broken.
    # It would use the same MIB as ucd_cpu_load, but with other
    # semantics. Please compare. Please mail us an cmk --snmpwalk of
    # such a device, if you have one.
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2021.10.1",
        oids=["6"],
    ),
    detect=contains(".1.3.6.1.2.1.1.1.0", "BX600"),
)


def discover_blade_bx_load(section: Section) -> DiscoveryResult:
    yield Service()


register.check_plugin(
    name="blade_bx_load",
    service_name="CPU load",
    discovery_function=discover_blade_bx_load,
    check_function=check_cpu_load,
    check_default_parameters={"levels": (5.0, 20.0)},
    check_ruleset_name="cpu_load",
)
