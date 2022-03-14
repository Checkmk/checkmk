#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.tcp_connections import TCPConnections


def parse_winperf_tcp_conn(string_table: StringTable) -> TCPConnections:
    """
    >>> from pprint import pprint
    >>> pprint(parse_winperf_tcp_conn([
    ...     ["1368619819.06", "638"],
    ...     ["2", "53267", "counter"],
    ...     ["4", "3", "rawcount"],
    ...     ["6", "23", "rawcount"],
    ...     ["8", "1", "rawcount"],
    ...     ["10", "1", "rawcount"],
    ...     ["12", "12", "rawcount"],
    ...     ["14", "34830", "counter"],
    ...     ["16", "18437", "counter"],
    ... ]))
    {'ESTABLISHED': 3}

    """
    section = {}
    for tcp_state, count, *_ in string_table:
        if tcp_state != "4":
            continue
        try:
            section["ESTABLISHED"] = int(count)
        except ValueError:
            pass
    return section


register.agent_section(
    name="winperf_tcp_conn",
    parse_function=parse_winperf_tcp_conn,
    parsed_section_name="tcp_conn_stats",
)
