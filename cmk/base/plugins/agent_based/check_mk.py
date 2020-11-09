#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from .agent_based_api.v1 import register, HostLabel


def parse_checkmk_labels(string_table):
    """
    Example:

        <<<check_mk>>>
        Version: 1.7.0
        BuildDate: Sep 15 2020
        AgentOS: windows
        Hostname: MSEDGEWIN10
        Architecture: 64bit

    """
    return {line[0].rstrip(':'): ' '.join(line[1:]) for line in string_table}


def host_label_function_labels(section):
    if 'AgentOS' in section:
        yield HostLabel("cmk/os_family", section['AgentOS'])


register.agent_section(
    name="check_mk",
    parse_function=parse_checkmk_labels,
    host_label_function=host_label_function_labels,
)
