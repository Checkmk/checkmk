#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from .agent_based_api.v1 import HostLabel, register


def parse_labels(string_table):
    """Load json dicts

    Example:

        <<<labels:sep(0)>>>
        {"tier": "control-plane", "component": "kube-scheduler"}

    """
    labels = {}
    for line in string_table:
        labels.update(json.loads(line[0]))
    return labels


def host_label_function_labels(section):
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


register.agent_section(
    name="labels",
    parse_function=parse_labels,
    host_label_function=host_label_function_labels,
)
