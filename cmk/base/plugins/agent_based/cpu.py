#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.cpu import Load, Section, Threads


def parse_cpu(string_table: StringTable) -> Optional[Section]:
    """
    Output is taken from /proc/loadavg plus the number of cores:

    >>> string_table = ['0.26 0.47 0.52 2/459 19531 4'.split()]
    >>> print(parse_cpu(string_table))
    Section(load=Load(load1=0.26, load5=0.47, load15=0.52), num_cpus=4, threads=Threads(count=459, max=None), type=<ProcessorType.unspecified: 0>)
    >>> string_table = ['0.26 0.47 0.52 2/459 19531 4'.split(), ['124069']]
    >>> print(parse_cpu(string_table))
    Section(load=Load(load1=0.26, load5=0.47, load15=0.52), num_cpus=4, threads=Threads(count=459, max=124069), type=<ProcessorType.unspecified: 0>)

    """
    if not string_table or len(string_table[0]) < 5:
        return None

    row = string_table[0]

    if len(row) >= 6:
        # There have been broken AIX agents for a long time which produced data like follows.
        # Newer agents deal with this, but to be nice to old agents: deal with it.
        # <<<cpu>>>
        # 0.00 0.00 0.00 1/97 8913088 aixxyz configuration: @lcpu=8 @mem=24576MB @ent=0.20
        for part in row:
            if "lcpu=" in part:
                num_cpus = int(part.split("=", 1)[1])
                break
        else:
            num_cpus = int(row[5])
    else:
        num_cpus = 1

    section = Section(
        num_cpus=num_cpus,
        load=Load(float(row[0]), float(row[1]), float(row[2])),
        threads=Threads(
            count=int(row[3].split("/")[1]),
            max=int(string_table[1][0]) if len(string_table) > 1 else None,
        ),
    )

    return section


register.agent_section(
    name="cpu",
    parse_function=parse_cpu,
    supersedes=["ucd_cpu_load"],
)
