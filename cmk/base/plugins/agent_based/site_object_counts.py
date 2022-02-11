#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Mapping, Optional

from .agent_based_api.v1 import Metric, register, Result, Service
from .agent_based_api.v1 import State as state
from .agent_based_api.v1 import type_defs

Section = Dict[str, Dict[str, Mapping[str, int]]]


def parse_site_object_counts(string_table: type_defs.StringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_site_object_counts([
    ... ['[[[stable]]]'],
    ... ['Tags', 'snmp prod', '2;2'],
    ... ['Service check commands', 'omd_apache hr_cpu', '2;1'],
    ... ]))
    {'stable': {'Service check commands': {'hr_cpu': 1, 'omd_apache': 2},
                'Tags': {'prod': 2, 'snmp': 2}}}
    """
    parsed: Section = {}
    site_objects = None
    for line in string_table:
        line0 = line[0]
        if line0.startswith("[[[") and line0.endswith("]]]"):
            site = line0[3:-3]
            site_objects = parsed.setdefault(site, {})
            continue

        cmds_or_tags, header, counts = line
        if site_objects is not None and counts:
            site_objects.setdefault(
                cmds_or_tags,
                {k: int(v) for k, v in zip(header.split(), counts.split(";"))},
            )
    return {k: v for k, v in parsed.items() if v}


register.agent_section(
    name="site_object_counts",
    parse_function=parse_site_object_counts,
)


def discover_site_object_counts(section: Section) -> type_defs.DiscoveryResult:
    if section:
        yield Service()


def check_site_object_counts(section: Section) -> type_defs.CheckResult:

    global_counts: Dict[str, Dict[str, int]] = {}
    for site, site_data in section.items():
        site_info = []
        for cmds_or_tags, counts in site_data.items():
            global_cmds_or_tags_counts = global_counts.setdefault(cmds_or_tags, {})
            site_counts = []
            for counted_obj, count in counts.items():
                global_cmds_or_tags_counts.setdefault(counted_obj, 0)
                global_cmds_or_tags_counts[counted_obj] += count
                site_counts.append("%s %s" % (count, counted_obj))
            site_info.append("%s: %s" % (cmds_or_tags.title(), ", ".join(site_counts)))
        yield Result(
            state=state.OK,
            notice="[%s] %s" % (site, ", ".join(site_info)),
        )

    global_info = []
    for cmds_or_tags, counts in global_counts.items():
        cmds_or_tags_info = []
        for counted_obj, count in counts.items():
            yield Metric(
                ("%s %s" % (cmds_or_tags, counted_obj)).lower().replace(" ", "_").replace(".", "_"),
                count,
            )
            cmds_or_tags_info.append("%s %s" % (count, counted_obj))
        global_info.append("%s: %s" % (cmds_or_tags.title(), ", ".join(cmds_or_tags_info)))

    yield Result(
        state=state.OK,
        summary=", ".join(global_info),
    )


def cluster_check_site_object_counts(
    section: Mapping[str, Optional[Section]]
) -> type_defs.CheckResult:
    yield from check_site_object_counts(
        {
            "%s/%s" % (site_name, node_name): site_counts
            for node_name, node_section in section.items()
            for site_name, site_counts in (node_section.items() if node_section is not None else ())
        }
    )


register.check_plugin(
    name="site_object_counts",
    service_name="OMD objects",  # Leave 'OMD' to be consistent (OMD %s apache,...)
    discovery_function=discover_site_object_counts,
    check_function=check_site_object_counts,
    cluster_check_function=cluster_check_site_object_counts,
)
