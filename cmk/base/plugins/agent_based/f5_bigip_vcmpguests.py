#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""F5-BIGIP-Cluster-Status SNMP Sections and Checks
"""

from typing import List, Mapping, Optional

from .agent_based_api.v1 import all_of, register, Result, Service, SNMPTree
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.f5_bigip import F5_BIGIP, VERSION_V11_2_PLUS

Section = Mapping[str, str]


def parse_f5_bigip_vcmpguests(string_table: List[StringTable]) -> Optional[Section]:
    """Read a node status encoded as stringified int
    >>> parse_f5_bigip_vcmpguests([[['guest1', 'Active'], ['guest2', 'Inactive']]])
    {'guest1': 'active', 'guest2': 'inactive'}
    """
    return {guest: status.lower() for guest, status in string_table[0]} or None


def discovery_f5_bigip_vcmpguests(section: Section) -> DiscoveryResult:
    yield Service()


def check_f5_bigip_vcmpguests(section: Section) -> CheckResult:
    for guest, status in sorted(section.items()):
        yield Result(state=state.OK, summary="Guest [%s] is %s" % (guest, status))


register.snmp_section(
    name="f5_bigip_vcmpguests",
    detect=all_of(F5_BIGIP, VERSION_V11_2_PLUS),
    parse_function=parse_f5_bigip_vcmpguests,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.3375.2.1.13.4.2.1",
            oids=[
                "1",  # sysVcmpStatVcmpName
                "17",  # sysVcmpStatPrompt
            ],
        ),
    ],
)

register.check_plugin(
    name="f5_bigip_vcmpguests",  # name taken from pre-1.7 plugin
    service_name="BIG-IP vCMP Guests",
    discovery_function=discovery_f5_bigip_vcmpguests,
    check_function=check_f5_bigip_vcmpguests,
)
