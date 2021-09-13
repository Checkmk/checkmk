#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List

from .agent_based_api.v1 import HostLabel, register
from .agent_based_api.v1.type_defs import HostLabelGenerator, StringTable

Section = Dict[str, Dict[str, Dict[str, str]]]


def parse_omd_info(string_table: StringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_omd_info([
    ...     ['[versions]'],
    ...     ['version', 'number', 'edition', 'demo'],
    ...     ['v1.full', 'v1', 'full', '0'],
    ...     ['v2.full', 'v2', 'full', '0'],
    ...     ['[sites]'],
    ...     ['site', 'used_version', 'autostart'],
    ...     ['heute', 'v1', '0'],
    ...     ['beta', 'v2', '0'],
    ... ]))
    {'sites': {'beta': {'autostart': '0', 'site': 'beta', 'used_version': 'v2'},
               'heute': {'autostart': '0', 'site': 'heute', 'used_version': 'v1'}},
     'versions': {'v1.full': {'demo': '0',
                              'edition': 'full',
                              'number': 'v1',
                              'version': 'v1.full'},
                  'v2.full': {'demo': '0',
                              'edition': 'full',
                              'number': 'v2',
                              'version': 'v2.full'}}}
    """
    section: Section = {}
    current_subsection: Dict[str, Dict[str, str]] = {}
    headers: List[str] = []
    for line in (l for l in string_table if l):
        if line[0][0] == "[" and line[0][-1] == "]":
            current_subsection = section.setdefault(line[0].strip("[]"), {})
            headers = []  # 'reset'
            continue

        if not headers:
            headers = line
            continue

        current_subsection[line[0]] = dict(zip(headers, line))

    return section


def host_label_omd_info(section: Section) -> HostLabelGenerator:
    if section.get("sites"):
        yield HostLabel("cmk/check_mk_server", "yes")


register.agent_section(
    name="omd_info",
    parse_function=parse_omd_info,
    host_label_function=host_label_omd_info,
)
