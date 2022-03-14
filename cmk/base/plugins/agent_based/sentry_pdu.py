#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, NamedTuple, Optional

from .agent_based_api.v1 import equals, register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable


class PDU(NamedTuple):
    state: str
    power: Optional[int]


Section = Mapping[str, PDU]

_STATES_INT_TO_READABLE = {
    "0": "off",
    "1": "on",
    "2": "off wait",
    "3": "on wait",
    "4": "off error",
    "5": "on error",
    "6": "no comm",
}


def parse_sentry_pdu(string_table: StringTable) -> Section:
    """
    >>> parse_sentry_pdu([["TowerA_InfeedA", "1", "1097"], ["TowerA_InfeedB", "21", "0"], ["TowerA_InfeedC", "1", ""]])
    {'TowerA_InfeedA': PDU(state='on', power=1097), 'TowerA_InfeedB': PDU(state='unknown', power=0), 'TowerA_InfeedC': PDU(state='on', power=None)}
    """
    return {
        name: PDU(
            _STATES_INT_TO_READABLE.get(
                state,
                "unknown",
            ),
            int(power_str) if power_str else None,
        )
        for name, state, power_str in string_table
    }


register.snmp_section(
    name="sentry_pdu",
    parse_function=parse_sentry_pdu,
    detect=equals(
        ".1.3.6.1.2.1.1.2.0",
        ".1.3.6.1.4.1.1718.3",
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1718.3.2.2.1",
        oids=[
            "3",
            "5",
            "12",
        ],
    ),
)
