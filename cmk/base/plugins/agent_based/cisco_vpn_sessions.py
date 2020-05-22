#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v0 import SNMPTree, any_of, contains, register


def parse_cisco_vpn_sessions(string_table):
    parsed = {}
    for idx, session_type in enumerate(['IPsec', 'SVC', 'WebVPN']):
        try:
            parsed[session_type] = int(string_table[0][0][idx])
        except ValueError:
            continue
    return parsed


register.snmp_section(
    name="cisco_vpn_sessions",
    parse_function=parse_cisco_vpn_sessions,
    detect=any_of(
        contains('.1.3.6.1.2.1.1.1.0', 'cisco pix security'),
        contains('.1.3.6.1.2.1.1.1.0', 'cisco adaptive security'),
    ),
    trees=[
        SNMPTree(
            base='.1.3.6.1.4.1.9.9.392.1.3',
            oids=[
                '26',  # crasIPSecNumSessions
                '35',  # crasSVCNumSessions
                '38',  # crasWebvpnNumSessions
            ],
        ),
    ],
)
