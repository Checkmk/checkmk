#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Final, List, Optional, Tuple, Union
from .agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register

SectionDict = Dict[str, Union[List[Tuple[str, int]],  #
                              List[Tuple[str, List[str]]],  # TODO: .util.cpu_util.CPUInfo?
                             ]]

Section = Tuple[Optional[int], SectionDict]


KERNEL_COUNTER_NAMES: Final[Dict[str, str]] = {  # order determines the service output!
    "processes": "Process Creations",
    "ctxt": "Context Switches",
    "pgmajfault": "Major Page Faults",
    "pswpin": "Page Swap in",
    "pswpout": "Page Swap Out",
}


def parse_kernel(string_table: StringTable) -> Section:
    """
        >>> from pprint import pprint
        >>> pprint(parse_kernel([
        ...     ['11238'],
        ...     ['nr_free_pages', '198749'],
        ...     ['pgpgin', '169984814'],
        ...     ['pgpgout', '97137765'],
        ...     ['pswpin', '250829'],
        ...     ['pswpout', '751706'],
        ...     ['pgmajfault', '1795031'],
        ...     ['cpu', '13008772', '12250', '5234590', '181918601',
        ...      '73242', '0', '524563', '0', '0', '0'],
        ... ])[1])
        {'Cpu Utilization': [('cpu',
                              ['13008772',
                               '12250',
                               '5234590',
                               '181918601',
                               '73242',
                               '0',
                               '524563',
                               '0',
                               '0',
                               '0'])],
         'Major Page Faults': [('pgmajfault', 1795031)],
         'Page Swap Out': [('pswpout', 751706)],
         'Page Swap in': [('pswpin', 250829)]}

    """
    try:
        timestamp: Optional[int] = int(string_table[0][0])
    except (IndexError, ValueError):
        timestamp = None

    parsed: Dict[str, List] = {}
    for line in string_table[1:]:
        if line[0] in KERNEL_COUNTER_NAMES:
            try:
                parsed.setdefault(KERNEL_COUNTER_NAMES[line[0]], []).append((line[0], int(line[1])))
            except (IndexError, ValueError):
                continue

        if line[0].startswith('cpu'):
            try:
                parsed.setdefault('Cpu Utilization', []).append((line[0], line[1:]))
            except (IndexError, ValueError):
                continue
    return timestamp, parsed


register.agent_section(
    name="kernel",
    parse_function=parse_kernel,
)
