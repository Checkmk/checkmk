#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import AgentSection, HostLabel, HostLabelGenerator, StringTable

Section = dict[str, dict[str, dict[str, str]]]


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
    current_subsection: dict[str, dict[str, str]] = {}
    headers: list[str] = []
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
    """Host label function

    Labels:

        cmk/check_mk_server:
            This label is set to "yes" if the section contains site information

    """
    if section.get("sites"):
        yield HostLabel("cmk/check_mk_server", "yes")


agent_section_omd_info = AgentSection(
    name="omd_info",
    parse_function=parse_omd_info,
    host_label_function=host_label_omd_info,
)
