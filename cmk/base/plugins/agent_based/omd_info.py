#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict
from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import AgentStringTable

Section = Dict[str, Dict[str, str]]


def parse_omd_info(string_table: AgentStringTable) -> Section:
    """
    >>> for k, v in parse_omd_info([
    ...         ['[versions]'],
    ...         ['version', 'number', 'edition', 'demo'],
    ...         ['v1.full', 'v1', 'full', '0'],
    ...         ['v2.full', 'v2', 'full', '0'],
    ...         ['[sites]'],
    ...         ['site', 'used_version', 'autostart'],
    ...         ['heute', 'v1', '0'],
    ...         ['stable', 'v2', '0'],
    ... ]).items():
    ...     print(k)
    ...     for k2, v2 in v.items():
    ...         print("  ", k2, v2)
    versions
       v1.full {'version': 'v1.full', 'number': 'v1', 'edition': 'full', 'demo': '0'}
       v2.full {'version': 'v2.full', 'number': 'v2', 'edition': 'full', 'demo': '0'}
    sites
       heute {'site': 'heute', 'used_version': 'v1', 'autostart': '0'}
       stable {'site': 'stable', 'used_version': 'v2', 'autostart': '0'}
    """
    result = {}
    current_section: Dict[str, str] = {}
    headers = None
    for line in string_table:
        if not line:
            continue
        if line[0][0] == "[" and line[0][-1] == "]":
            current_section = {}
            result[line[0].strip("[]")] = current_section
            headers = None
        elif current_section is not None:
            if headers is None:
                headers = list(map(str, line))
            else:
                current_section[line[0]] = dict(zip(headers, line))
    return result


register.agent_section(name="omd_info", parse_function=parse_omd_info)
