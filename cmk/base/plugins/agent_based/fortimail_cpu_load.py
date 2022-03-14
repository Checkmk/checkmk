#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Optional, Tuple

from .agent_based_api.v1 import check_levels, register, Service, SNMPTree
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.fortinet import DETECT_FORTIMAIL

Section = Mapping[str, float]


def parse_fortimail_cpu_load(string_table: StringTable) -> Optional[Section]:
    """
    >>> parse_fortimail_cpu_load([["5"]])
    {'cpu_load': 5.0}
    """
    return {"cpu_load": float(string_table[0][0])} if string_table else None


def discovery_fortimail_cpu_load(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortimail_cpu_load(
    params: Mapping[str, Optional[Tuple[float, float]]],
    section: Section,
) -> CheckResult:
    yield from check_levels(
        section["cpu_load"],
        levels_upper=params["cpu_load"],
        metric_name="load_instant",
        label="CPU load",
    )


register.snmp_section(
    name="fortimail_cpu_load",
    parse_function=parse_fortimail_cpu_load,
    detect=DETECT_FORTIMAIL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.105.1",
        oids=[
            "30",  # fmlSysLoad
        ],
    ),
)

register.check_plugin(
    name="fortimail_cpu_load",
    service_name="CPU load",
    discovery_function=discovery_fortimail_cpu_load,
    check_function=check_fortimail_cpu_load,
    check_default_parameters={"cpu_load": None},
    check_ruleset_name="fortimail_cpu_load",
)
