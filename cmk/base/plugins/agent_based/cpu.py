#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List, Optional, Union
from .agent_based_api.v1.type_defs import AgentStringTable

from .agent_based_api.v1 import register

Section = Dict[str, Union[float, List[float]]]


def parse_cpu(string_table: AgentStringTable) -> Optional[Section]:
    """
        Output is taken from /proc/loadavg plus the number of cores:

        >>> from pprint import pprint
        >>> string_table = ['0.26 0.47 0.52 2/459 19531 4'.split()]
        >>> pprint(parse_cpu(string_table))
        {'load': [0.26, 0.47, 0.52], 'num_cpus': 4, 'num_threads': 459}

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

    section: Section = {
        'num_cpus': num_cpus,
        'load': [float(i) for i in row[0:3]],
        'num_threads': int(row[3].split('/')[1]),
    }

    if len(string_table) > 1:
        section['max_threads'] = int(string_table[1][0])

    return section


register.agent_section(
    name="cpu",
    parse_function=parse_cpu,
)
