#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

from ..agent_based_api.v1 import type_defs

GenericSection = Dict[str, Dict[str, Dict[str, str]]]


def generic_parse(string_table: type_defs.StringTable) -> GenericSection:
    """
    >>> from pprint import pprint
    >>> pprint(generic_parse([
    ... ['fcStats', 'Dn sys/switch-B/slot-1/switch-fc/port-1/stats', 'BytesRx 27132984565284',
    ...  'BytesTx 2905866392424', 'PacketsRx 13332284889', 'PacketsTx 1589971733', 'Suspect no']]))
    {'fcStats': {'sys/switch-B/slot-1/switch-fc/port-1/stats': {'BytesRx': '27132984565284',
                                                                'BytesTx': '2905866392424',
                                                                'Dn': 'sys/switch-B/slot-1/switch-fc/port-1/stats',
                                                                'PacketsRx': '13332284889',
                                                                'PacketsTx': '1589971733',
                                                                'Suspect': 'no'}}}
    """
    result: GenericSection = {}
    for line in string_table:
        module = line[0]
        # Pylint complains about the unnecessary use of a comprehension here. However, changing this
        # for example to
        # elements = dict(tuple(x.split(" ", 1)) for x in line[1:])
        # will make Mypy unhappy (Tuple[str, ...] vs Tuple[<nothing>, <nothing>])
        # pylint: disable=unnecessary-comprehension
        elements = {k: v for k, v in (x.split(" ", 1) for x in line[1:])}
        if elements.get("Dn"):
            result.setdefault(module, {}).update({elements["Dn"]: elements})

    return result


UCS_FAULTINST_SEVERITY_TO_STATE = {
    "critical": 2,
    "major": 1,
    "warning": 1,
    "minor": 1,
    "info": 0,
    "condition": 0,
    "cleared": 0,
}
