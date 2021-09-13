#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register, type_defs
from .utils.netapp_api import CPUSection

# 7mode
# <<<netapp_api_cpu:sep(9)>>>
# cpu_busy        8362860064
# num_processors  2

# clustermode
# cpu-info clu1-01        num_processors 2
# cpu-info clu1-02        num_processors 2
# cpu-info clu1-01        cpu_busy 5340000        nvram-battery-status battery_ok
# cpu-info clu1-02        cpu_busy 5400000        nvram-battery-status battery_ok


def parse_netapp_api_cpu(string_table: type_defs.StringTable) -> CPUSection:
    """
    >>> from pprint import pprint
    >>> pprint(parse_netapp_api_cpu([
    ... ['cpu_busy', '8362860064'],
    ... ['num_processors', '2'],
    ... ]))
    {'7mode': {'cpu_busy': '8362860064', 'num_processors': '2'}}
    >>> pprint(parse_netapp_api_cpu([
    ... ['cpu-info clu1-01', 'num_processors 2'],
    ... ['cpu-info clu1-02', 'num_processors 2'],
    ... ['cpu-info clu1-01', 'cpu_busy 5340000', 'nvram-battery-status battery_ok'],
    ... ['cpu-info clu1-02', 'cpu_busy 5400000', 'nvram-battery-status battery_ok'],
    ... ]))
    {'clustermode': {'clu1-01': {'cpu_busy': '5340000',
                                 'num_processors': '2',
                                 'nvram-battery-status': 'battery_ok'},
                     'clu1-02': {'cpu_busy': '5400000',
                                 'num_processors': '2',
                                 'nvram-battery-status': 'battery_ok'}}}
    """
    cpu_info: CPUSection = {}
    for line in string_table:
        if line[0].startswith("cpu-info"):  # clustermode
            _, node_name = line[0].split()
            cpu_info.setdefault("clustermode", {})
            for entry in line[1:]:
                key, value = entry.split()
                cpu_info["clustermode"].setdefault(node_name, {})
                cpu_info["clustermode"][node_name][key] = value
        else:
            cpu_info.setdefault("7mode", {})
            cpu_info["7mode"][line[0]] = line[1]
    return cpu_info


register.agent_section(
    name="netapp_api_cpu",
    parse_function=parse_netapp_api_cpu,
)
