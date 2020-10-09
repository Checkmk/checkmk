#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, NamedTuple, Optional
from .agent_based_api.v1.type_defs import AgentStringTable

from .agent_based_api.v1 import register


class Peer(NamedTuple):
    statecode: str
    name: str
    refid: str
    stratum: str
    t: str
    when: str
    poll: str
    reach: str
    delay: str
    offset: str
    jitter: str


Section = Dict[Optional[str], Peer]


def parse_ntp(string_table: AgentStringTable) -> Section:
    section: Section = {}
    for line in string_table:
        if len(line) != 11:
            continue
        peer = Peer(*line)
        section[peer.name] = peer
        if None not in section and peer.statecode in '*o':  # keep first one!
            section[None] = peer

    return section


register.agent_section(
    name="ntp",
    parse_function=parse_ntp,
)
