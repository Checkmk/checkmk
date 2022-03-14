#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register, SNMPTree
from .utils.arbor import DETECT_PEAKFLOW_SP, parse_arbor_cpu_load

register.snmp_section(
    name="arbor_peakflow_sp_cpu_load",
    parsed_section_name="cpu",
    parse_function=parse_arbor_cpu_load,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.4.2.1",
        oids=[
            "1.0",  # deviceCpuLoadAvg1min
            "2.0",  # deviceCpuLoadAvg5min
            "3.0",  # deviceCpuLoadAvg15min
        ],
    ),
    detect=DETECT_PEAKFLOW_SP,
)
