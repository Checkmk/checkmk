#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from .agent_based_api.v1 import register, HostLabel


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
    for pair in section.items():
        yield HostLabel(*pair)


register.agent_section(
    name="labels",
    parse_function=parse_labels,
    host_label_function=host_label_function_labels,
)
