#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.14685.3.1.12.1.0 10 --> DATAPOWER-STATUS-MIB::dpStatusTCPSummaryestablished.0
# .1.3.6.1.4.1.14685.3.1.12.2.0 2 --> DATAPOWER-STATUS-MIB::dpStatusTCPSummarysynsent.0
# .1.3.6.1.4.1.14685.3.1.12.3.0 0 --> DATAPOWER-STATUS-MIB::dpStatusTCPSummarysynreceived.0
# .1.3.6.1.4.1.14685.3.1.12.4.0 0 --> DATAPOWER-STATUS-MIB::dpStatusTCPSummaryfinwait1.0
# .1.3.6.1.4.1.14685.3.1.12.5.0 0 --> DATAPOWER-STATUS-MIB::dpStatusTCPSummaryfinwait2.0
# .1.3.6.1.4.1.14685.3.1.12.6.0 15 --> DATAPOWER-STATUS-MIB::dpStatusTCPSummarytimewait.0
# .1.3.6.1.4.1.14685.3.1.12.7.0 0 --> DATAPOWER-STATUS-MIB::dpStatusTCPSummaryclosed.0
# .1.3.6.1.4.1.14685.3.1.12.8.0 0 --> DATAPOWER-STATUS-MIB::dpStatusTCPSummaryclosewait.0
# .1.3.6.1.4.1.14685.3.1.12.9.0 0 --> DATAPOWER-STATUS-MIB::dpStatusTCPSummarylastack.0
# .1.3.6.1.4.1.14685.3.1.12.10.0 24 --> DATAPOWER-STATUS-MIB::dpStatusTCPSummarylisten.0
# .1.3.6.1.4.1.14685.3.1.12.11.0 0 --> DATAPOWER-STATUS-MIB::dpStatusTCPSummaryclosing.0
from typing import List

from .agent_based_api.v1 import OIDEnd, register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable
from .utils import datapower, tcp_connections


def parse_datapower_tcp(string_table: List[StringTable]) -> tcp_connections.TCPConnections:
    """
    >>> from pprint import pprint
    >>> pprint(parse_datapower_tcp([[
    ...     [u'1.0', u'10'],
    ...     [u'2.0', u'2'],
    ...     [u'3.0', u'0'],
    ...     [u'4.0', u'0'],
    ...     [u'5.0', u'0'],
    ...     [u'6.0', u'15'],
    ...     [u'7.0', u'0'],
    ...     [u'8.0', u'0'],
    ...     [u'9.0', u'0'],
    ...     [u'10.0', u'24'],
    ...     [u'11.0', u'0']
    ... ]]))
    {'CLOSED': 0,
     'CLOSE_WAIT': 0,
     'CLOSING': 0,
     'ESTABLISHED': 10,
     'FIN_WAIT1': 0,
     'FIN_WAIT2': 0,
     'LAST_ACK': 0,
     'LISTEN': 24,
     'SYN_RECV': 0,
     'SYN_SENT': 2,
     'TIME_WAIT': 15}

    """
    section = tcp_connections.empty_stats()
    for raw_key, raw_value in string_table[0]:
        key = tcp_connections.MAP_COUNTER_KEYS.get(int(raw_key.split(".")[0]))
        if key is None:
            continue
        section[key] = int(raw_value)
    return section


register.snmp_section(
    name="datapower_tcp",
    parsed_section_name="tcp_conn_stats",
    parse_function=parse_datapower_tcp,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.14685.3.1",
            oids=[
                OIDEnd(),  # state of tcp connection
                "12",  # number of tcp connections of this state
            ],
        ),
    ],
    detect=datapower.DETECT,
)
