#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from .agent_based_api.v1 import register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable
from .utils.cpu import Load, Section
from .utils.mcafee_gateway import DETECT_EMAIL_GATEWAY


def parse_mcafee_emailgateway_cpuload(string_table: StringTable) -> Optional[Section]:
    """
    >>> parse_mcafee_emailgateway_cpuload([["1.234"]])
    Section(load=Load(load1=1.234, load5=1.234, load15=1.234), num_cpus=1, threads=None, type=<ProcessorType.unspecified: 0>)
    """
    if not string_table:
        return None
    load = float(string_table[0][0])
    return Section(
        load=Load(
            load1=load,
            load5=load,
            load15=load,
        ),
        num_cpus=1,
    )


register.snmp_section(
    name="mcafee_emailgateway_cpuload",
    parsed_section_name="cpu",
    parse_function=parse_mcafee_emailgateway_cpuload,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.4.1.2.3.1",
        oids=[
            "2",  # loadaverage
        ],
    ),
    detect=DETECT_EMAIL_GATEWAY,
)
