#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping

from .agent_based_api.v1 import check_levels, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.tcp_connections import empty_stats, MAP_COUNTER_KEYS, TCPConnections


def parse_tcp_conn_stats(string_table: StringTable) -> TCPConnections:
    """
    >>> from pprint import pprint
    >>> pprint(parse_tcp_conn_stats([
    ...     ["01", "29"],
    ...     ["02", "3"],
    ...     ["0A", "26"],
    ...     ["05", "1"],
    ...     ["06", "187"],
    ... ]))
    {'CLOSED': 0,
     'CLOSE_WAIT': 0,
     'CLOSING': 0,
     'ESTABLISHED': 29,
     'FIN_WAIT1': 0,
     'FIN_WAIT2': 1,
     'LAST_ACK': 0,
     'LISTEN': 26,
     'SYN_RECV': 0,
     'SYN_SENT': 3,
     'TIME_WAIT': 187}

    >>> pprint(parse_tcp_conn_stats([
    ...     ["LISTEN", "39"],
    ...     ["IDLE", "3"],
    ...     ["TIME_WAIT", "1"],
    ...     ["ESTABLISHED", "68"],
    ...     ["BOUND", "1"],
    ... ]))
    {'BOUND': 1,
     'CLOSED': 0,
     'CLOSE_WAIT': 0,
     'CLOSING': 0,
     'ESTABLISHED': 68,
     'FIN_WAIT1': 0,
     'FIN_WAIT2': 0,
     'IDLE': 3,
     'LAST_ACK': 0,
     'LISTEN': 39,
     'SYN_RECV': 0,
     'SYN_SENT': 0,
     'TIME_WAIT': 1}

    """
    section = empty_stats()  # TODO: use counter
    for tcp_state, count, *_ in string_table:
        if len(tcp_state) == 2:
            try:
                tcp_state = MAP_COUNTER_KEYS[int(tcp_state, 16)]  # Hex
            except KeyError:
                continue
        try:
            section[tcp_state] = int(count)
        except ValueError:
            pass
    return section


register.agent_section(
    name="tcp_conn_stats",
    parse_function=parse_tcp_conn_stats,
)


def discover_tcp_connections(section: TCPConnections) -> DiscoveryResult:
    if any(value != 0 for value in section.values()):
        yield Service()


def check_tcp_connections(params: Mapping[str, Any], section: TCPConnections) -> CheckResult:
    for tcp_state, tcp_count in sorted(section.items()):
        label = tcp_state.replace("_", " ").capitalize()
        yield from check_levels(
            tcp_count,
            levels_upper=params.get(tcp_state),
            metric_name=tcp_state,
            render_func=lambda i: "%d" % i,
            label=label,
            notice_only=(label != "Established"),
        )


register.check_plugin(
    name="tcp_conn_stats",
    service_name="TCP Connections",
    discovery_function=discover_tcp_connections,
    check_function=check_tcp_connections,
    check_default_parameters={},
    check_ruleset_name="tcp_conn_stats",
)
