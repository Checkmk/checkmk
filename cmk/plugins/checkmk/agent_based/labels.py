#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Mapping

from cmk.agent_based.v2 import AgentSection, HostLabel, HostLabelGenerator, StringTable

Section = Mapping[str, str]


def parse_labels(string_table: StringTable) -> Section:
    """Load json dicts

    Example:

        <<<labels:sep(0)>>>
        {"tier": "control-plane", "component": "kube-scheduler"}

    """
    labels = {}
    for line in string_table:
        labels.update(json.loads(line[0]))
    return labels


def host_label_function_labels(section: Section) -> HostLabelGenerator:
    """Host label function

    Labels:

        This function creates host labels according to the '<<<labels>>>'
        section sent by the agent(s).

    Example:

        >>> section = {"tier": "control-plane", "component": "kube-scheduler"}
        >>> for hl in host_label_function_labels(section):
        ...     print(str(hl))
        HostLabel('tier', 'control-plane')
        HostLabel('component', 'kube-scheduler')

    """
    for pair in section.items():
        yield HostLabel(*pair)


agent_section_labels = AgentSection(
    name="labels",
    parse_function=parse_labels,
    host_label_function=host_label_function_labels,
)
