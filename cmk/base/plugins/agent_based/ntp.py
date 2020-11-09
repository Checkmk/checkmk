#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, NamedTuple, Optional
from .agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register


class Peer(NamedTuple):
    statecode: str
    name: str
    refid: str
    stratum: int
    when: int
    reach: str
    offset: float
    jitter: float


Section = Dict[Optional[str], Peer]


def _ntp_fmt_time(raw: str) -> int:
    if raw == '-':
        return 0
    if raw[-1] == "m":
        return int(raw[:-1]) * 60
    if raw[-1] == "h":
        return int(raw[:-1]) * 60 * 60
    if raw[-1] == "d":
        return int(raw[:-1]) * 60 * 60 * 24
    return int(raw)


def parse_ntp(string_table: StringTable) -> Section:
    section: Section = {}
    for line in string_table:
        if len(line) != 11:
            continue
        peer = Peer(
            statecode=line[0],
            name=line[1],
            refid=line[2],
            stratum=int(line[3]),
            when=_ntp_fmt_time(line[5]),
            reach=line[7],
            offset=float(line[9]),
            jitter=float(line[10]),
        )
        section[peer.name] = peer
        if None not in section and peer.statecode in '*o':  # keep first one!
            section[None] = peer

    return section


register.agent_section(
    name="ntp",
    parse_function=parse_ntp,
)
