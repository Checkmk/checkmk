#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from time import time
from typing import Mapping, Tuple, TypedDict

from .agent_based_api.v1 import get_value_store, register, Service, SNMPTree
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.cpu_util import check_cpu_util
from .utils.juniper import DETECT

Section = Mapping[str, int]


def parse_juniper_cpu_util(string_table: StringTable) -> Section:
    return {
        raw_name.replace("@ ", "").replace("/*", "").strip(): int(raw_util)
        for raw_name, raw_util in string_table
        if raw_util
    }


register.snmp_section(
    name="juniper_cpu_util",
    parse_function=parse_juniper_cpu_util,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2636.3.1.13.1",
        oids=[
            "5",  # jnxOperatingDescr
            "8",  # jnxOperatingCPU
        ],
    ),
    detect=DETECT,
)


class CheckParams(TypedDict):
    levels: Tuple[float, float]


def discover_juniper_cpu_util(section: Section) -> DiscoveryResult:
    """
    >>> list(discover_juniper_cpu_util({"a": 1, "b": 0}))
    [Service(item='a')]
    """
    # JUNIPER-MIB::jnxOperatingCPU
    # The CPU utilization in percentage of this subject. Zero if unavailable or inapplicable.
    # Zeros can mean two things: zero utilization or this device has no CPU. There is unfortunately
    # no way to distinguish these two cases. We cannot simply reject zeros in the parse function,
    # otherwise, a device which actually has a CPU but with currently zero utilization will go stale
    # ==> brilliant construct, Juniper!
    yield from (Service(item=device) for device, util in section.items() if util)


def check_juniper_cpu_util(
    item: str,
    params: CheckParams,
    section: Section,
) -> CheckResult:
    if (util := section.get(item)) is None:
        return
    yield from check_cpu_util(
        util=util,
        params=params,
        this_time=time(),
        value_store=get_value_store(),
    )


register.check_plugin(
    name="juniper_cpu_util",
    service_name="CPU utilization %s",
    discovery_function=discover_juniper_cpu_util,
    check_function=check_juniper_cpu_util,
    check_ruleset_name="juniper_cpu_util",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)
